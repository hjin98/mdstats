---
title: "mdstats MLFF Training-Data Architecture"
subtitle: "Canonical architecture and staged implementation"
author: "mdstats project"
date: "2026-08-17 (revision 90: TARGET-DATA2B-FEAS1-PERF3 global single-level scheduling)"
geometry: margin=0.78in
toc: true
toc-depth: 3
numbersections: true
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{longtable}
  - |-
    \usepackage{microtype}
  - |-
    \usepackage{xurl}
---

# Revision 90 current gate: TARGET-DATA2B-FEAS1-PERF3 global single-level scheduling and campaign progress

`mdstats 0.20.223a0` replaces PERF2 after workstation observation showed that profile-local block threading still left substantial CPU capacity unused and that progress lines such as `family ... blocks=47/49` did not state how many profiles remained. The scientific FEAS1 authority is unchanged.

PERF3 removes nested parallelism from production FEAS1. Instead of factoring the CPU budget as Python block threads x native cKDTree workers inside one profile, the stage creates one campaign-wide queue spanning every label domain, profile/family, and witness block. Automatic mode assigns one executor worker to each CPU-budget lane and every parallel `query_ball_point` task uses `workers=1`. On a 32-logical-thread workstation with the frozen 90% CPU fraction, this means 28 independent FEAS1 executor lanes. A lane finishing a block or an entire profile immediately consumes the next queued block from any other active profile, eliminating the profile-tail starvation inherent to PERF2.

Profile/tree preparation is also submitted to the same executor, so later-profile cKDTree construction can overlap ongoing query/compression work. The scheduler keeps up to `2 x workers` futures pending and bounds pending plus completed-but-not-reduced block results at `4 x workers`; this gives the executor enough ready work to maintain occupancy without allowing ragged neighbor arrays to grow without bound.

Scientific reduction is still profile-local and deterministic. Blocks may complete globally out of order, but candidate-gain updates are delayed until each profile's next contiguous witness block is available. The PERF1 canonical row-major/candidate-major compressor and historical FP64 `np.add.at` order are unchanged, so report dictionaries and digests remain invariant to the new schedule.

Progress is now campaign-wide. FEAS1 pre-counts profiles, blocks, and witnesses before expensive work starts. Periodic output reports profiles completed/total, profiles prepared/total, active profiles, global block/witness completion, sampled busy executor lanes, pending/queued work, elapsed time, throughput, and global ETA. A profile-completion line uses completion count as the leading fraction and lists the deterministic manifest ordinal separately.

## Frozen revision-90 execution contract

| Item | Value |
|---|---|
| FEAS1 scientific schema/digest | unchanged |
| Parallel topology | one global single-level queue across all domains/profiles/blocks |
| Automatic global workers | full `StageResourceScope` CPU budget |
| Parallel cKDTree workers/task | exactly 1 |
| Default 32-thread workstation budget | 28 global FEAS1 workers at `cpu_fraction=0.90` |
| Pending future bound | `2 x global_workers` |
| Pending + ready result bound | `4 x global_workers` |
| New execution override | `target_coverage_feasibility_global_workers` |
| PERF2/PERF1 worker settings | compatibility aliases |
| Deterministic reduction | per-profile contiguous witness order |
| Global progress | profiles, blocks, witnesses, busy lanes, queue, elapsed, rate, ETA |
| GPU neighborhood authority | unchanged; not authorized |
| TARGET-DATA2C scientific selection | unchanged |

On the qualification host, eight profiles of 25,033 witnesses each (eight-dimensional exact neighborhoods, 512-witness blocks) improved from 7.793 s with serial-profile/native-tree-8 execution to 3.811 s with the global-8/tree-1 queue, a 2.04x wall-time speedup. The global evaluator consumed 29.178 s of process CPU in 3.811 s wall time, corresponding to 7.66 average cores or 95.7% of its eight assigned lanes. Exact family-report dictionaries were identical. This is execution evidence only.

# Revision 89 historical gate: TARGET-DATA2B-FEAS1-PERF2 block parallelism and long-wall progress

`mdstats 0.20.222a0` revises the PERF1 execution schedule after direct workstation observation still showed only about 200-500% aggregate CPU during a long FEAS1 run. The PERF1 vectorized exact neighborhood kernel remains authoritative; this revision changes only how independent witness blocks are scheduled and how long-wall progress is reported.

The remaining utilization loss came from one Python driver issuing one 512-witness `cKDTree.query_ball_point` at a time. Native cKDTree workers are active only inside that query, while the compiled ragged-neighborhood compression that follows is a separate phase. Family-level concurrency therefore provides little help when a domain has only one or a few expensive families.

PERF2 schedules independent witness blocks concurrently with a bounded `ThreadPoolExecutor` sharing one read-only scaled descriptor matrix and one cKDTree. Each block may itself use a small number of native cKDTree workers. `StageResourceScope` continues to enforce `block_workers * tree_workers <= cpu_threads_budget`. Automatic mode uses at most eight block workers, normally at most four tree workers per block, and searches bounded factorizations for high lane occupancy. On a 32-thread host with the default 90% CPU budget, a representative automatic factorization is 7 block workers x 4 tree workers = 28 bounded lanes. A single-block family may still use up to sixteen tree workers.

A fork/process block backend was prototyped and rejected as the automatic path. Although it creates multiple visible Python processes, exact deterministic reduction requires sending compressed ragged neighborhood arrays back to the parent. On the eight-thread qualification host that IPC path was substantially slower than shared-memory block threading. Process count is therefore not treated as a utilization target; sustained CPU occupancy and wall time are the performance criteria.

Block futures may finish out of order, but scientific reduction is performed only in contiguous witness order. PERF1's canonical row-major/candidate-major pair ordering is preserved inside every block, so candidate-gain FP64 addition order, support-degree arrays, support-mass accumulation, coverage lower bounds, and report digests are unchanged.

FEAS1 now emits family start plus block/witness progress with elapsed wall time, average witness rate, and ETA. The parent wait loop uses `[performance].progress_interval_seconds` as a heartbeat timeout, so a slow in-flight query cannot leave the terminal silent indefinitely. TARGET-DATA2C-MVIDX1 receives matching block-level progress with accumulated edge counts because one sparse-index family may also run for a long wall time. Progress is execution-only.

## Frozen revision-89 execution contract

| Item | Value |
|---|---|
| FEAS1 scientific schema/digest | unchanged |
| Query topology | concurrent witness blocks sharing one read-only cKDTree |
| Automatic block workers | bounded, up to 8 |
| Automatic tree workers per block | normally up to 4; single-block path up to 16 |
| CPU budget | `block_workers * tree_workers <= StageResourceScope budget` |
| New execution override | `target_coverage_feasibility_block_workers` |
| PERF1 family-worker setting | retained as compatibility alias |
| Deterministic reduction | completed blocks buffered and reduced in witness order |
| FEAS1 progress | block/witness count, elapsed, rate, ETA + heartbeat |
| MVIDX1 progress | block/witness count, elapsed, rate, ETA, edge count |
| GPU neighborhood authority | unchanged; not authorized |
| TARGET-DATA2C scientific selection | unchanged |

On the eight-thread qualification host (seven-thread 90% CPU budget), an 8,192-witness three-dimensional synthetic exact-neighborhood family improved from about 0.30 s with one Python driver and seven native cKDTree workers to about 0.19 s with three concurrent blocks and two tree workers per block (about 1.6x), with exact family-report dictionary equivalence. Allowing all eight lanes as four blocks x two tree workers reached about 0.16 s (about 1.9x). The evaluated process-block prototype took about 1.27 s and was rejected. These timings are execution evidence only, not scientific tuning data.

# Revision 88 historical gate: TARGET-DATA2B-FEAS1-PERF1 exact CPU hardening

`mdstats 0.20.221a0` hardens the execution path of TARGET-DATA2B-FEAS1 after workstation observation showed long wall time with low average CPU utilization and an idle GPU. The scientific FEAS1 authority, fixed 16,384 ceiling, exact cKDTree neighborhoods, FP64 accumulation order, and all downstream selector identities remain unchanged. This revision is execution-only.

The observed utilization pattern followed directly from the revision-67 implementation. Native cKDTree workers were active only during each 512-witness `query_ball_point` call. Every returned ragged neighborhood was then reduced by a Python loop over individual witnesses using `np.unique`, scalar support-degree bookkeeping, and one candidate-gain update at a time. Automatic execution also capped the tree at eight native workers. Thus the query phase could use several cores while the reduction phase repeatedly collapsed to one Python execution lane; CUDA was never part of this exact CPU authority.

Revision 88 replaces the per-witness reduction with a bounded vectorized exact kernel. For one query block, geometric neighbor rows are mapped to owning candidate frames, packed as `(local_witness_row, candidate_frame)` int64 keys, reduced with compiled `np.unique`, and returned in canonical row-major/candidate-major order. Candidate gain uses `np.add.at` in that same historical order. Self-excluded and correlation-unit-excluded degrees are computed from vectorized bincounts, retained for the whole family, then accumulated once in original witness order with `np.add.accumulate`. This preserves the scalar FP64 addition sequence and makes the scientific report invariant to query-block partitioning.

Independent feature families now execute concurrently under the existing `StageResourceScope`. Automatic FEAS1 scheduling divides the configured CPU budget between family workers and cKDTree workers rather than dedicating the whole stage to one eight-thread tree. When enough families exist, automatic mode targets roughly four native tree lanes per concurrent family; a single family may use up to sixteen tree workers. The new optional `[performance].target_coverage_feasibility_family_workers` setting overrides only the execution schedule. Existing `[performance].target_coverage_workers` remains the native tree-worker override. The CLI prints family workers, tree workers per family, query block, and the resulting bounded CPU-lane product.

The same canonical vectorized row-compression kernel is used by TARGET-DATA2C-MVIDX1. MVIDX1 therefore no longer loops in Python over every witness solely to deduplicate candidate-frame ownership before writing the canonical sparse row stream. Persisted uint32/uint64 graph arrays, edge ordering, hashes, and downstream MVSEL1/REPAIR1 scientific plans remain unchanged.

GPU execution is deliberately not introduced. FEAS1/MVIDX1 neighborhood authority is exact SciPy cKDTree CPU work; moving it to CUDA would create a new distance/threshold realization that would require separate equivalence qualification. Consequently low GPU utilization during these stages is expected and is not a defect. GPU qualification remains deferred to FINAL-GPU1 as previously frozen.

## Frozen revision-88 execution contract

| Item | Value |
|---|---|
| FEAS1 scientific schema/digest | unchanged |
| Coverage metric/radii | unchanged exact TARGET-DATA2B cKDTree relation |
| Candidate-frame deduplication | vectorized packed `(row,candidate)` unique reduction |
| FP64 candidate-gain order | historical row-major/candidate-major order |
| Support-mass order | historical witness order |
| Family scheduling | bounded concurrent ThreadPool execution |
| Automatic native tree workers | CPU-budget partition; up to 16 for single-family execution |
| New execution override | `target_coverage_feasibility_family_workers` |
| MVIDX1 sparse row construction | same vectorized canonical kernel |
| GPU authority | unchanged; not used |
| TARGET-DATA2C scientific selection | unchanged |

The focused FEAS1/MVIDX1 and downstream MVSEL1/REPAIR1/MVPERF1 suites require exact dictionary/digest equivalence across worker, block, and family-parallel schedules. On the eight-thread development host, a four-family 8,192-candidate synthetic exact-equivalence benchmark improved from about 1.63 s for the historical scalar reduction to about 0.99 s for the optimized bounded schedule (approximately 1.65x) with identical family reports. The benchmark is execution evidence only, not scientific tuning data.

# Revision 87 historical gate: WARN-DOMAIN1 campaign-wide warning capture

`mdstats 0.20.220a0` replaces the accumulated operation-by-operation warning suppression patches with one command-wide warning domain at the MLFF campaign CLI boundary. The scientific training/data/parity contracts are unchanged from revision 86; this gate changes only runtime warning transport, grouping, and presentation.

The campaign command now owns the outermost `mace_runtime_warning_scope` from argument dispatch until the command returns or fails. Existing operation-local decorators remain in place, but under campaign execution they only register their operation name into the outer domain. This closes setup/recovery gaps in which MACE/PyTorch warnings could be emitted immediately before or after a locally decorated provider call.

Python warning capture and Python logging are treated as separate ingress mechanisms into the same authority. All MACE/PyTorch warnings that reach Python's `warnings` machinery are grouped by origin/category/source/message. MACE/PyTorch `logging.WARNING` or higher records are identified from the emitting source pathname or package logger name, captured through a temporary campaign logging interceptor, and prevented from reaching raw handlers. This includes MACE 0.3.16 root-logger messages such as the `Default dtype float32 does not match model dtype float64` conversion warning.

The outer campaign domain is process-wide for the lifetime of one CLI command in addition to using the existing `ContextVar`. This is required because worker threads do not necessarily inherit the main-thread context. A local MACE warning scope entered in a worker therefore binds to the same campaign record rather than creating and emitting a second warning summary. Operation-name merging is thread-safe.

At command exit mdstats emits at most one normalized `[WARN]` line containing the total raw count and unique grouped MACE/PyTorch warning signatures. Raw TorchScript `DeprecationWarning` lines and `WARNING:root:` MACE messages must not appear. Unrelated Python warnings and unrelated logging remain outside this compatibility policy and retain their existing behavior rather than being silently discarded. Standalone library/API calls outside `mdstats-mlff-campaign` retain the historical operation-local consolidated `MaceRuntimeCompatibilityWarning` behavior.

## Frozen revision-87 warning-domain contract

| Item | Value |
|---|---|
| Campaign owner | one outer warning domain per CLI command |
| Python warning coverage | entire command lifetime |
| Logging coverage | MACE/PyTorch `WARNING+`, including root logger |
| Worker-thread local scopes | merge into campaign owner |
| Nested operation scopes | merge operation names; no independent emission |
| Campaign presentation | one normalized `[WARN]` summary |
| Raw MACE/PyTorch warning/log leak | forbidden |
| Unrelated warning/logging behavior | preserved |
| Standalone API behavior | historical local scope retained |
| Scientific DATA/TRAIN2/parity identity | unchanged from revision 86 |

# Revision 86 historical gate: CUEQ-REPEAT1-PARITY1 permanent TRAIN2 FP32 noise-normalized parity

`mdstats 0.20.219a0` replaces the stochastic one-shot TRAIN2 FP32 force `allclose` gate with an authorizing warm-up/all-pairs criterion derived from the MPA-0 DIAG3 workstation evidence. The source/DATA6 and stable TRAIN2 energy/stress/descriptor policy is again `rtol=1e-5, atol=1e-6`; only TRAIN2 FP32 force equivalence uses the new self-noise normalization.

The ordinary production path discards one warm-up evaluation per backend and retains ten post-warm-up outputs from e3nn and pure CuEq. The resulting `45 + 45 + 100` self/cross pairs are the authorization evidence. For force RMSE, p99, and p99.9, mdstats compares the p99 cross statistic against the larger p99 self-backend envelope and requires a ratio no greater than `1.25`. Cross `Fmax` is no longer the primary gate; it is a catastrophic guard bounded by `min(1.5 x self Fmax envelope, 1e-4 eV/A)`.

The frozen MPA-0 DIAG3 ordinary evidence gives approximate p99 ratios `1.08` (`Frmse`), `1.02` (`Fp99`), and `0.90` (`Fp99.9`), while the maximum cross `Fmax=2.261e-5` remains below the same-backend envelope `2.337e-5`. Selection is identical in all 100 cross pairs. The deterministic-control evidence shows post-warm-up e3nn self pairs collapse to exact zero but CuEq remains stochastic, demonstrating that the relevant force tail is intrinsic FP32 CuEq execution noise rather than a systematic cross-backend model shift.

All self/cross selections must remain identical; all values must remain finite. No ratio or Fmax limit adapts after seeing a failed run. The deterministic-control subprocess remains available for investigation but is not executed during routine authorization. FINAL-GPU1 preflight v10 binds both the stable-channel and noise-normalized policy digests.

## Frozen revision-86 policy

| Item | Value |
|---|---|
| Warm-up | `1` discarded complete evaluation/backend |
| Post-warm-up samples | `10` e3nn + `10` pure CuEq |
| Pair populations | `45` e3nn-self, `45` CuEq-self, `100` cross |
| Stable E/S/D ceiling | `1e-6` maximum absolute cross-pair error |
| Force distribution statistic | p99 across pair metrics |
| Force metrics | `Frmse`, `Fp99`, `Fp99.9` |
| Cross/self ratio ceiling | `1.25` |
| Fmax self-envelope factor | `1.5` |
| Fmax absolute catastrophic ceiling | `1e-4 eV/A` |
| Selection identity | mandatory for every self/cross pair |
| Repeatability evidence | repeatability diagnostic v2 |
| Authorizing parity record | noise-normalized parity record v1 |
| Routine deterministic-control probe | disabled; optional diagnostic only |

# Revision 85 historical gate: CUEQ-REPEAT1-DIAG3 warm-up + all-pairs repeatability diagnostic

`mdstats 0.20.218a0` performs the final measurement refinement before the TRAIN2 FP32 backend-equivalence policy is redesigned. Revision-84 MPA-0/default evidence confirmed that ordinary and deterministic-control force variability is comparable within e3nn-self, CuEq-self, and e3nn/CuEq comparisons. Ordinary `Fmax` maxima were `1.962e-5` (e3nn-self), `1.836e-5` (CuEq-self), and `2.270e-5` (cross). Under the isolated deterministic controls they were `1.061e-5`, `2.709e-5`, and `1.550e-5`, respectively. Selection remained identical throughout.

The deterministic e3nn self result was exactly `1.061e-5` for every run-1-versus-later-run comparison. Because the temporary diagnostic used run 1 as the common self reference, that pattern is consistent with a first-call/warm-up shift contaminating every self statistic. DIAG3 therefore removes the arbitrary baseline rather than altering any tolerance.

Each e3nn and pure-CuEq calculator now receives one complete **discarded warm-up evaluation** on the exact doctor probe. mdstats then retains ten post-warm-up outputs per backend and computes all scalar comparison metrics offline: `C(10,2)=45` e3nn-self pairs, `45` CuEq-self pairs, and `10x10=100` cross-backend pairs. This adds only one discarded model evaluation per backend relative to DIAG2 while increasing statistical coverage substantially.

Every pair carries `Fmax`, force RMSE, force absolute-error p99 and p99.9, count `|dF| > 1e-5`, energy/stress/descriptor errors, and selection identity where applicable. Terminal output reports `min`, `median`, `p90`, `p99`, and `max` distributions plus exact pair/selection counts; it does not print all 100 cross pairs. The full pairwise scalar arrays are persisted.

The ordinary diagnostic schema advances to `mdstats.training-acceleration-repeatability-diagnostic.v2` with `comparison_mode=all_pairs` and `warmup_count=1`. Historical v1 records remain readable under their original baseline semantics. The isolated deterministic-control subprocess uses the same DIAG3 algorithm and retains its outer v1 wrapper.

Revision 85 remains **non-authorizing**. TRAIN2 FP32 parity remains `rtol=1e-5, atol=1e-5`; source/DATA6 and FP64 policies remain unchanged. FINAL-GPU1 stays archival until DIAG3 workstation evidence is interpreted and a separate noise-normalized parity criterion is frozen.

## Frozen revision-85 diagnostic contract

| Item | Value |
|---|---|
| Discarded warm-up | `1` complete evaluation per backend |
| Post-warm-up samples | `10` e3nn + `10` pure-CuEq |
| e3nn-self comparisons | `45` all unordered pairs |
| CuEq-self comparisons | `45` all unordered pairs |
| Cross comparisons | `100` Cartesian-product pairs |
| Force metrics | `Fmax`, `Frmse`, `Fp99`, `Fp99.9`, count `|dF| > 1e-5` |
| Other channels | `Emax`, `Smax`, `Dmax`, selection identity |
| Printed quantiles | `min`, `median`, `p90`, `p99`, `max` |
| Ordinary record | `mdstats.training-acceleration-repeatability-diagnostic.v2` |
| Deterministic control | same warm-up/all-pairs algorithm in isolated subprocess |
| Authorizing | **No** |
| TRAIN2 FP32 tolerance | unchanged `rtol=1e-5`, `atol=1e-5` |

# Revision 84 historical gate: CUEQ-REPEAT1-DIAG2 full self-tail + deterministic-control refinement

`mdstats 0.20.217a0` refines the revision-83 non-authorizing TRAIN2 FP32 repeatability diagnostic after the MPA-0/default workstation measurement showed that **same-backend repeatability noise is at least as large as the paired e3nn/pure-CuEq discrepancy**. Across the reported 10-repeat probe, e3nn-self `Fmax` had median `1.422e-5`, p90 `1.779e-5`, and max `2.120e-5`; CuEq-self had median `1.196e-5`, p90 `1.978e-5`, and max `2.076e-5`; paired e3nn/CuEq had median `1.013e-5`, p90 `1.696e-5`, and max `1.699e-5`. Paired force RMSE remained `2.023e-6` to `3.374e-6`, at most 3 of 90 force components exceeded `1e-5` in any paired repeat, and selection identity was `10/10`. Energy/stress/descriptor maxima remained predominantly at the `1e-7` scale.

This evidence demonstrates that the current one-shot force maximum is strongly affected by run-to-run FP32 GPU execution noise. Revision 84 therefore **does not widen or replace the active parity gate**. TRAIN2 FP32 remains `rtol=1e-5, atol=1e-5`; source/DATA6 and FP64 policies remain unchanged. The purpose of this gate is to obtain enough same-backend and controlled-determinism evidence to define a later noise-normalized equivalence criterion without guessing another absolute ceiling.

The ordinary execution-path diagnostic now records and prints the same force-tail statistics for e3nn-self and CuEq-self that were already available for paired cross-backend comparisons: `Fmax`, force RMSE, absolute-error p99, p99.9, and the count of force components above `1e-5`. Self comparisons remain run 1 versus runs 2-10 so the revision-83 measurements stay directly comparable.

Revision 84 also adds an **isolated deterministic-control subprocess**. The subprocess is launched fresh so reproducibility controls are established before CUDA initialization. It sets `CUBLAS_WORKSPACE_CONFIG=:4096:8`, enables `torch.use_deterministic_algorithms(True)`, sets deterministic debug mode to `error`, disables cuDNN benchmarking, and enables deterministic cuDNN behavior. It then reruns the same 10-repeat e3nn/pure-CuEq diagnostic on a geometry-only copy of the exact doctor probe corpus and selected TRAIN2 checkpoint/head.

The deterministic-control probe is diagnostic only. If all operations support deterministic execution, doctor prints a second `[DIAG-DET]` statistics block with the same full self/cross metrics. If PyTorch, CuEq, or another CUDA operation cannot provide a deterministic implementation, the worker returns `unsupported_or_failed` and doctor prints the exact exception; it must not silently fall back to a nondeterministic or e3nn-only execution path. The ordinary production-path diagnostic always remains separate from the deterministic control so qualification continues to characterize the runtime intended for training.

The refined ordinary record remains the existing repeatability-diagnostic v1 schema with backward-readable optional self-tail fields. The isolated control uses a separate deterministic-control-diagnostic v1 schema and is stored under campaign state key `training_acceleration_deterministic_control_diagnostic`. Both records are explicitly **non-authorizing**.

## Frozen revision-84 diagnostic contract

| Item | Value |
|---|---|
| Ordinary repetitions | `10` e3nn + `10` pure-CuEq evaluations |
| Ordinary self metrics | `Fmax`, `Frmse`, `Fp99`, `Fp99.9`, count `|dF| > 1e-5` |
| Cross metrics | unchanged revision-83 full paired statistics |
| Deterministic control | isolated fresh subprocess, same 10-repeat corpus |
| CUBLAS deterministic workspace | `:4096:8` |
| PyTorch deterministic algorithms | forced `True` in control subprocess |
| Deterministic debug mode | `error` |
| cuDNN benchmark | `False` |
| cuDNN deterministic | `True` |
| Unsupported deterministic operation | print/persist failure; no fallback |
| Authorizing effect | none |
| Active FP32 TRAIN2 gate | unchanged `rtol=1e-5, atol=1e-5` |



# Revision 83 historical gate: CUEQ-REPEAT1-DIAG TRAIN2 FP32 repeatability diagnostic hotfix

`mdstats 0.20.216a0` adds a non-authorizing repeated numerical diagnostic around the phase-separated TRAIN2 e3nn/pure-CuEq parity check. The diagnostic is motivated by MPA-0/default workstation reruns in which the one-shot force maximum was not stable: reported `Fmax` values included approximately `1.371e-5`, `1.059e-5`, and `2.897e-5`, followed by a later run that fell below the active `1e-5` TRAIN2 ceiling, while energy/stress/descriptor maxima remained near `1e-7` and deterministic selection remained identical. A one-shot extreme-value statistic is therefore insufficient to distinguish a stable backend offset from within-backend GPU nondeterminism.

The hotfix does **not** change the revision-82 parity authority. TRAIN2 FP32 remains `rtol=1e-5, atol=1e-5`; source/DATA6 FP32 remains `rtol=1e-5, atol=1e-6`; FP64 remains `rtol=1e-10, atol=1e-12`. The existing one-shot parity record remains the authorizing gate until repeatability evidence is reviewed. No tolerance is widened, no aggregate statistic is promoted to a pass criterion, and no silent fallback is introduced.

When a phase-separated TRAIN2 campaign requests pure CuEq in FP32 and CuEq is available, `doctor` now performs a **10-repeat diagnostic** on the same deterministic probe corpus and exact selected training checkpoint/head. Each repetition evaluates e3nn and pure CuEq once. Runs 2-10 are also compared with run 1 inside each backend to measure same-backend force repeatability. The paired e3nn/CuEq comparisons report, for every repetition:

- energy maximum absolute difference;
- force maximum absolute difference and force RMSE;
- absolute force-error p99 and p99.9;
- count of force components above the reporting threshold `1e-5`;
- stress and descriptor maximum absolute differences; and
- deterministic selection identity.

The terminal then prints aggregate `min / median / p90 / max` summaries for e3nn-self `Fmax`, CuEq-self `Fmax`, paired cross-backend `Fmax`, `Frmse`, `Fp99`, and `Fp99.9`, plus aggregate counts above `1e-5`. The runtime report also prints PyTorch deterministic-algorithm state, deterministic debug mode, cuDNN determinism, and `CUBLAS_WORKSPACE_CONFIG`. These settings are observations only; this diagnostic hotfix does not force deterministic algorithms because doing so could change the execution path being characterized.

The diagnostic is serialized as `mdstats.training-acceleration-repeatability-diagnostic.v1` under campaign state key `training_acceleration_repeatability_diagnostic`. It is content-addressed and explicitly **non-authorizing**. A diagnostic failure produces a warning rather than silently changing the TRAIN2 acceleration decision.

The revision-82 FINAL-GPU1 v3/HF2 workstation bundle is archival for release authorization while this repeatability investigation is open. After workstation values are reported, the measured e3nn-self, CuEq-self, and cross-backend envelopes will determine whether the parity statistic/policy needs a further scientifically justified revision.

## Frozen revision-83 diagnostic contract

| Item | Value |
|---|---|
| Repetitions | `10` e3nn + `10` pure-CuEq evaluations |
| Corpus | same deterministic TRAIN2 doctor probe |
| Model/head | exact selected TRAIN2 checkpoint and resolved head |
| Same-backend comparison | each run 2-10 versus run 1 |
| Cross-backend comparison | paired e3nn/CuEq per repetition |
| Force reporting threshold | `1e-5` (diagnostic count only) |
| Authorizing effect | none |
| Active FP32 TRAIN2 gate | unchanged `rtol=1e-5, atol=1e-5` |

# Revision 82 historical gate: CUEQ-DEFAULT1-HF2 TRAIN2 FP32 backend-parity ceiling hotfix

`mdstats 0.20.215a0` applies a narrowly scoped numerical-equivalence hotfix to the phase-separated TRAIN2 CuEq preflight. The generic ACCEL1 source/DATA6 FP32 parity authority remains `rtol=1e-5, atol=1e-6`; only the TRAIN2 FP32 absolute ceiling changes, from `2e-6` to `1e-5`, while retaining `rtol=1e-5`. FP64 remains unchanged at `rtol=1e-10, atol=1e-12`.

The revision is motivated by MACE-MPA-0/default workstation evidence reporting `Emax=2.384e-7`, `Fmax=8.911e-6`, `Smax=1.660e-7`, and `Dmax=2.883e-7` with `selection_identical=True`. The observed pattern is consistent with backend-dependent non-associative FP32 reduction/accumulation order: energy, stress, and descriptor channels remain near the FP32 roundoff scale while a force reduction reaches the high-`1e-6` range. The `1e-5` value is therefore frozen as a **backend-equivalence envelope**, not a training-convergence, validation, model-accuracy, or deployment tolerance.

The ceiling is intentionally fixed rather than data-adaptive. All outputs must remain finite, deterministic selection identity remains mandatory, and a zero-reference absolute delta greater than `1e-5` remains a failure. No observed failure may auto-widen the tolerance and no silent e3nn fallback is introduced. Scientific convergence and model-quality criteria remain at their independently defined scales.

FINAL-GPU1 remains v3 with the existing 18-item matrix, but preflight advances from v8 to v9. The v9 preflight and handoff manifest persist the exact TRAIN2 acceleration-parity policy payload and digest; handoff integrity verification recomputes the active policy and rejects a mismatch. A revision-81/v8 preflight or release archive therefore cannot authorize the hotfixed release.

## Frozen revision-82 TRAIN2 parity contract

| Authority | FP32 `rtol` | FP32 `atol` | FP64 `rtol` | FP64 `atol` |
|---|---:|---:|---:|---:|
| Generic source/DATA6 ACCEL1 | `1e-5` | `1e-6` | `1e-10` | `1e-12` |
| TRAIN2 pure-CuEq/e3nn equivalence | `1e-5` | `1e-5` | `1e-10` | `1e-12` |

The MPA-0/default evidence point `Fmax=8.911e-6` is inside the TRAIN2 envelope. A regression anchor at `1.0001e-5` against a zero reference is outside the envelope and must fail. This fixed upper boundary prevents the numerical-equivalence gate from becoming an implicit adaptive tolerance.

# Revision 80 current gate: REPLAY-UNIFY1D single-source campaign integration

`mdstats 0.20.213a0` advances the frozen REPLAY-UNIFY1 migration through `REPLAY-UNIFY1D`. The public campaign boundary now uses one `[paths].replay_set` file. mdstats owns replay qualification, deterministic train/monitor partitioning, true-label and foundation-pseudo-label logical views, and disposable MACE-compatible transport materialization. Historical split-file campaigns remain readable through an explicitly deprecated compatibility path.

Gate D intentionally preserves the downstream TRAIN2/DATA8 scientific contracts by introducing an adapter boundary: the new replay authority creates authenticated internal `replay_train`/`replay_monitor` transport artifacts under `.mdstats/replay-unified`, and the existing TRAIN2/DATA8 machinery consumes those derived artifacts exactly as before. The split files are no longer external configuration authority. This reduces migration risk while making the new single-source interface effective immediately.

For `true_dft`, the single replay source is validated and split directly, with true-label train and monitor views materialized lazily. For `foundation_pseudolabel`, `prepare` resolves the doctor-frozen acceleration realization, builds or reuses the Gate-C batched foundation prediction cache and qualification authority, freezes the qualified split, materializes pseudo-label train/monitor views, and independently materializes the true-label monitor view from the exact same split. Production pseudo-label campaigns therefore fail closed if the requested retention truth is unavailable.

New generated configuration exposes only `--replay-set` and `[paths].replay_set`; the old `--replay-train`, `--replay-monitor`, and `--replay-true-labels` flags remain hidden parser-compatible inputs for historical automation. Mixing the new and legacy replay interfaces is forbidden. `doctor` validates the single replay source, source truth, and runtime prerequisites but deliberately defers the expensive full foundation prediction pass to `prepare`, where it becomes persistent campaign authority.

Restart authority now includes the single-source config, replay source, true-label cache, foundation prediction/qualification records when applicable, split manifest, and materialized-view receipts. A persisted authenticated `ReplaySourceArtifact` receipt prevents 12,000-frame ExtXYZ reparsing on process-style restarts; generated transport views have their own SHA-bound historical `ReplayFileArtifact` receipts. Storage accounting protects the sole external `replay_set` input while treating `.mdstats/replay-unified` products as reconstructable campaign internals.

On the supplied 12,000-frame LTA replay source, the new campaign-facing `true_dft` path produced exactly 10,000 train and 2,000 monitor records. A cold end-to-end `_build_replay_plan()` including source inspection, true-label cache/split construction, internal materialization, and adapter artifact inspection required about 27.6 s on the development CPU host; a process-style restart after clearing only the in-memory context returned in about 0.60 s by reusing persisted source and transport receipts. Peak RSS was about 336 MB. These are host-specific integration measurements, not portable performance guarantees. Real foundation-model CUDA/CuEq execution remains deferred to the regenerated FINAL-GPU1 handoff after REPLAY-UNIFY1E.

## Frozen REPLAY-UNIFY1 external contract

New-style campaigns use one path and one semantic label mode:

```toml
[paths]
replay_set = "/path/to/replay_fps_12000.extxyz"

[replay]
label_mode = "foundation_pseudolabel"  # or "true_dft"
# split_ratio = "5:1"                  # optional; default 5:1
# split_seed = 42                       # optional; default 42
```

`[paths].replay_set` is the sole external replay authority. It may not be combined with legacy `[paths].replay_train`, `[paths].replay_monitor`, or `[paths].replay_true_labels`. Historical campaigns using those split-file fields remain readable through the legacy schema during migration, but generated new configurations will move to the single-source form only when REPLAY-UNIFY1D changes campaign execution.

The selected source file is not itself a training/monitor partition. It is an immutable replay-source authority from which mdstats derives all later replay products. Random/FPS source selection remains an upstream workflow and is deliberately outside REPLAY-UNIFY1.

## Five independently fingerprinted replay layers

Replay preparation is frozen as five independently invalidated layers:

```text
single replay source
       |
       v
SOURCE INDEX
canonical geometry identities + source-label inventory
       |
       v
LABEL CACHE
source truth and/or foundation predictions in distinct namespaces
       |
       v
QUALIFICATION
eligible geometry authority + audit metrics
       |
       v
SPLIT MANIFEST
exact deterministic train/monitor membership
       |
       v
MATERIALIZED VIEWS
only the MACE-compatible ExtXYZ products actually requested
```

The expensive label-prediction authority is therefore separated from cheap qualification, splitting, and file materialization. A ratio/seed change cannot trigger foundation-model inference. A qualification-threshold change reclassifies cached prediction/audit quantities without repaying inference. Deleting a materialized ExtXYZ causes only deterministic rematerialization. Foundation model/head/runtime changes invalidate pseudo-label prediction authority; source-geometry mutation invalidates every downstream replay authority.

## Canonical geometry and label namespaces

REPLAY-UNIFY1 introduces a new versioned canonical replay geometry identity, `mdstats.replay-geometry-identity.v1`. Atomic numbers and atom ordering are preserved; Cartesian positions and the cell are quantized to `1e-8 Angstrom`; PBC is explicit. The new identity is deliberately separate from historical `ReplayFileArtifact` v3/v4 geometry identity so old serialized artifacts are never silently reinterpreted.

Source truth and foundation predictions are distinct logical namespaces:

```text
source_true.energy / forces / stress
foundation_pseudolabel.energy / forces / stress
```

Neither namespace may overwrite the other internally. `REF_energy`, `REF_forces`, and `REF_stress` are transport-field names applied only when a requested MACE-compatible ExtXYZ view is materialized. This allows pseudo-label training and true-label retention evaluation to use exactly the same geometry membership without destroying the independent source truth.

## Qualification and split authority

The split ranking algorithm is label-independent, but the eligible set is qualification-bound. The immutable split manifest therefore binds the replay-source geometry-set identity, the eligible-geometry-set digest, the qualification-authority digest when one exists, the normalized train:monitor ratio, the split seed, and the exact train/monitor geometry identities.

For each eligible canonical geometry identity `g`, mdstats defines a deterministic rank from:

```text
SHA256("mdstats.replay-split-rank.v1" || seed || g)
```

and sorts by that rank. Membership is therefore independent of ExtXYZ ordering. The ratio is normalized to lowest integer terms; for `N` eligible configurations,

```text
N_train   = floor(N * w_train / (w_train + w_monitor))
N_monitor = N - N_train
```

with at least one configuration in each role. The default `5:1` rule maps an unfiltered 12,000-configuration selected replay corpus to exactly 10,000 training and 2,000 monitor configurations. Train and monitor must be disjoint and their union must equal the qualified geometry authority.

## Performance and restart contract

Foundation pseudo-label generation in REPLAY-UNIFY1C must reuse the optimized mdstats MACE batch path, bounded host-side batches, existing GPU/CuEq runtime controls, and content-addressed prediction caching. The historical standalone one-configuration-at-a-time `MACECalculator` loop is not production authority.

Materialized ExtXYZ views are caches/transport artifacts rather than configuration authority and are generated lazily. Typical pseudo-label training may need only `pseudo_train.extxyz` plus a true-label monitor view; unused pseudo/true combinations are not written eagerly. The pseudo-label cache fingerprint includes at least the exact foundation-model digest, resolved head identity, inference dtype, backend/CuEq contract, and relevant frozen MACE runtime identity.

The frozen invalidation policy is:

| Change | Re-index source | Re-run pseudo inference | Re-qualify | Re-split | Rematerialize |
|---|---:|---:|---:|---:|---:|
| Unchanged restart | no | no | no | no | only if missing |
| Split ratio or seed | no | no | no | yes | yes |
| Qualification threshold | no | no | yes | yes | yes |
| Additional label view requested | no | no | no | no | requested view only |
| Foundation model/head/runtime | no | yes | yes | yes | yes |
| Source-label payload only changes | revalidate source label namespace | mode-dependent | yes | only if eligible set changes | yes |
| Source geometry changes | yes | yes for pseudo mode | yes | yes | yes |

This invalidation matrix is an executable acceptance contract, not documentation-only guidance.

## Frozen implementation gates

REPLAY-UNIFY1 is divided into five ordered gates:

1. **REPLAY-UNIFY1A - authority and schemas.** Implement the single-source config record/parser, canonical geometry identity, streamed replay-source index/artifact, source-label namespace inventory, deterministic rank policy, immutable split manifest, exact 5:1 defaults, fail-closed mixed-interface validation, serialization round trips, and legacy split-file compatibility. Production TRAIN2/DATA8 behavior remains unchanged.
2. **REPLAY-UNIFY1B - true-label materialization.** Build true-label validation/cache authority directly from the one replay source, preserve exact source truth, bind all materialization to the split manifest, and lazily generate true-label train/monitor views without a separate `replay_true_labels` input.
3. **REPLAY-UNIFY1C - pseudo-label materialization.** Move replay pseudo-label/audit functionality into mdstats using batched cached MACE inference, independent foundation-label namespaces, model/head/runtime provenance, reusable raw prediction/audit caches, and threshold-only reclassification without reinference.
4. **REPLAY-UNIFY1D - campaign integration.** Route doctor/prepare/TRAIN2/DATA8/evaluation/storage/restart through logical replay roles, switch generated configuration to `[paths].replay_set`, remove split-file paths from new configs, and keep controlled deserialization of historical campaigns.
5. **REPLAY-UNIFY1E - migration, hardening, and optimization.** Qualify the invalidation matrix, source mutation, duplicate/overlap protection, true/pseudo geometry identity, restart reconstruction, lazy materialization, 12,000 -> 10,000/2,000 acceptance, throughput/memory behavior, documentation, and regeneration of the final one-shot FINAL-GPU1 bundle.

## REPLAY-UNIFY1A implementation boundary

Revision 77 implements Gate A only. New public contracts are additive and do not alter the live `ReplayPreparationPlan`, DATA8 membership, TRAIN2 jobs, replay-retention semantics, existing replay-file artifacts, or historical campaign restarts. `ReplaySourceArtifact` streams one selected ExtXYZ source into content-addressed geometry/source-label inventory. `ReplaySplitManifest` owns exact label-independent membership and can already bind a later qualification-authority digest. `ReplaySingleSourceConfig` normalizes `5:1`, defaults seed 42, rejects mixed new/legacy path authority, and can map historical `external_pseudolabel`/`external_true_label` mode strings only as a controlled migration convenience.

Gate-A acceptance requires deterministic source/split serialization, canonical duplicate rejection, exact 12,000 -> 10,000/2,000 membership, order-independent split membership, normalized-ratio equivalence, label inventory preservation, fail-closed mixed-interface parsing, and unchanged legacy replay behavior.

**Gate status:** REPLAY-UNIFY1 is complete: Gate A in `0.20.210a0`, Gate B in `0.20.211a0`, Gate C in `0.20.212a0`, Gate D in `0.20.213a0`, and Gate E in `0.20.214a0`. Gate E freezes the executable invalidation planner (`mdstats.replay-invalidation-plan.v1`), mutation/tamper/reconstruction qualification, source-relocation receipt reuse, 12,000 -> 10,000/2,000 acceptance, storage/performance review, and the regenerated FINAL-GPU1 v3 workstation handoff. Positive real MACE/CUDA/CuEq replay execution remains pending that one-shot workstation run.


# Revision 81 current gate: REPLAY-UNIFY1E closure and FINAL-GPU1 v3 regeneration

`mdstats 0.20.214a0` closes REPLAY-UNIFY1. The single selected replay corpus is the sole new-style external authority; train/monitor and true/pseudo views are deterministic authenticated internal materializations. Gate E makes the invalidation matrix executable through `ReplayInvalidationPlan`: unchanged restart performs no replay work; split-only changes re-split/rematerialize without inference; threshold-only changes requalify without inference; source-label-only mutation does not repredict pseudo-labels; foundation-policy or geometry changes invalidate pseudo predictions; missing views reconstruct from caches; and identical-byte source relocation rebinds the source receipt without ExtXYZ parsing.

FINAL-GPU1 is regenerated as v3. `REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION` is a must-pass CuEq-runtime-bound gate so the new batched replay path cannot acquire release authority from CPU/control-plane tests alone. Positive GPU execution remains pending on the final CUDA workstation.

# Revision 76 current gate: FINAL-GPU1 v2 workstation closure

`mdstats 0.20.209a0` completes the development-side `FINAL-GPU1` v2 release handoff. The immutable matrix now has nine must-pass gates, including typed `SIZE-FIDELITY2` and paired legacy-v4-versus-MV learning-control evidence required by `TARGET-DATA2C-MVMIGRATE1`. Both records must carry `gpu_qualification_status == "passed"`, must deserialize under their exact schemas, must match the content digests registered in the handoff root, and must share the campaign dataset identity. Generic pass/fail JSON cannot satisfy either requirement.

A positive FINAL-GPU1 v2 record does not directly mutate campaign defaults. `tools/activate_mlff_target_mv_migration.py` first reconstructs the authorized migration as a dry-run, then `--apply` performs one SQLite transaction that preserves TARGET-DATA2C v4 under a historical key and atomically publishes **TARGET-DATA2C v5 -> TARGET-DATA2D v3 -> TARGET-DATA2E v3** generation authority. The v5 ladder is rebuilt from exact REPAIR1 prefixes at 128, 256, 512, 1024, 2048, 4096, 8192, and 16384; v3 convergence requires at least four hard qualifiers; stale v2 production-decision and prepare-restart aliases are invalidated. Existing activation is accepted only when its content-addressed receipt matches exactly.

The release state is `workstation_ready`: positive GPU execution is still pending the one-shot final CUDA workstation run. Until that pass and explicit activation, the historical v4/v2/v2 production authority remains live.

# Purpose and status

This manual defines the high-level architecture for the
`mdstats.training_data` branch. The branch prepares source-certified atomistic
simulation data for machine-learned interatomic-potential training, especially
MACE foundation-model fine-tuning with multi-head replay.

This manual is the canonical architecture established at **MLFF-DATA0**. It
incorporates all architecture-review corrections directly into one plan.
MLFF-DATA1 is implemented in `0.20.29a0`: the source-independent
`mdstats.sampling` package now owns autocorrelation estimation, complete-frame
blocks, deterministic balanced assignment, and purged folds. Existing Stage 11
STAT1 and SAMP0 workflows consume those primitives without changing their
serialized evidence. MLFF-DATA2 is implemented in `0.20.30a0`: deterministic source manifests, VASP source catalogs, named energy selection, decomposed label domains, and per-label-domain structural atomic-reference identifiability are public runtime contracts. MLFF-DATA3 is implemented in `0.20.31a0`: manifest-bound frame occurrences, geometry and label identities, duplicate/restart detection, post-DFT eligibility, temperature conditions, reference-cell resolution, and rotation-separated finite strain are public runtime contracts. MLFF-DATA4 is implemented in `0.20.32a0` and generalized through DATA9A7d: partition-independent raw physical features, optional profile-extension states, protected event bursts, deterministic feature caches, and partition-role budget requests are public runtime contracts. MLFF-DATA5 is implemented in `0.20.33a0`: autocorrelation-aware partition units, role feasibility, deterministic outer evidence roles, independence grades, nested cross-validation monitors, blinding boundaries, and fail-closed leakage audits are public runtime contracts. MLFF-DATA6 is implemented in `0.20.34a0` and generalized through DATA9A7d: profile-aware universal and optional extension descriptors, optional checkpoint-bound MACE atomic descriptor sidecars, training-domain-only foundation residuals, blinded non-training predictions, and sealed locked-test prediction records are public runtime contracts. MLFF-DATA7 is implemented in `0.20.35a0`: canonical final/fold training domains, fold-local fitted metrics, domain-local atomic-reference fits, explicit objective and checkpoint policies, deterministic quota-interleaved selection ladders, and coverage reports are public runtime contracts. MLFF-DATA8 is implemented in `0.20.36a0`: verified MACE-readable extended-XYZ artifacts, explicit E0 mappings, replay train/monitor plans, a v0.3.16 source compatibility lock, complete training-protocol identities, loader dry-run exposure records, independent final/fold job bundles, and sealed locked-test metadata are public runtime contracts. MLFF-DATA9A hardening began in `0.20.37a0`, its offline runtime bootstrap is implemented in `0.20.38a0`, and DATA9A2 real-MACE realization is implemented in `0.20.39a0`: checkpoint-residual E0 fits, relocatable bundles, strict replay/XYZ audits, source-declared dependency manifests, isolated local-artifact installation, installed-environment qualification, v0.3.16 scalar-literal serialization, fixed-file target/replay weight realization, genuine parser/loader dry runs, bounded training, checkpoint/head inventory, target-head extraction, and finite evaluation round trips are public contracts. The supplied dependency bundle and MPA-0 checkpoint pass executable qualification. DATA9A3 in 0.20.40a0 qualifies the complete 27-source, 37,632-frame bulk-LTA target corpus through DATA5 with a passing leakage audit. DATA9A production execution remains open for checkpoint-bound production DATA6/DATA7 evidence, DATA8 job materialization, exact replay-corpus identity, and later protocol-matched training and freeze. DATA9A4 in 0.20.41a0 adds a protocol-bound selectable precision contract: the float64 MPA-0 checkpoint may initialize either a float32 or float64 fine-tuned model, and actual serialized parameter/buffer dtypes are immutable execution evidence rather than inferred from CLI text. DATA9A5a/9A5b in 0.20.42a0-0.20.43a0 close Python/ASE critical precision and deployment-artifact semantics. DATA9A6 in 0.20.44a0 introduces the analysis-owned observable-call bridge. DATA9A6b in 0.20.45a0 closes recipe dependency safety, collection and model lineage, runtime-duration/warning evidence, capability requirement schemas, documentation conflicts, and the thermomechanical/energetic analysis ownership plan. DATA9A6c in 0.20.46a0 verifies supplied identities against the actual collections, requires symmetric reference/candidate generation lineage for production evidence, binds analysis-owned result digests, freezes observable evidence roles and comparison-policy identity before locked evaluation, and corrects runtime/package identity and dependency ordering. DATA9A7a in 0.20.47a0 introduces user-declared compositional material profiles, phase components, atom-group catalogs, condition axes, independence axes, a declarative provider protocol, and DATA4 schema-v2 profile threading without changing existing feature or selection behavior. DATA9A7b in 0.20.48a0 adds an analysis-owned universal local-structure kernel, profile/atom-group-aware DATA6 structural catalogs, generic structural events, a DATA7 universal feature block, and generic per-species environment coverage without importing LTA. DATA9A7c in 0.20.49a0 derives immutable phase/geometry selection plans, profile-specific feature/event activation, geometry-aware atom-group priorities, DATA6-v3 plan lineage, and compositional observable-call recommendations. DATA9A7d in 0.20.50a0 migrates LTA behind generic optional profile-extension catalogs, advances DATA4/DATA6 canonical schemas, and replaces generic-core cation/site assumptions with focus groups, structural realizations, and extension coverage. DATA9A7e in 0.20.51a0 qualifies bounded crystal, amorphous, liquid, interface, and LTA DATA4-DATA7 paths, adds immutable qualification evidence, and makes MLFF LTA implementation imports lazy so generic workflows neither import nor serialize LTA-specific evidence. DATA9A8 in 0.20.52a0 adds frozen profile-aware observable comparison and acceptance policies. DATA9A9a in 0.20.53a0 adds the exact DATA5-authorized checkpoint-bound descriptor/prediction plan, per-frame restart sidecars, atomic checkpoints, corruption recovery, and DATA6 reuse without repeated foundation-model inference. DATA9A9b in 0.20.54a0 adds restartable final/fold DATA7 materialization, exact replay binding, complete DATA8 job-tree evidence, corruption-driven downstream invalidation, and a relocatable production materialization record. DATA9A9c in 0.20.55a0 adds the immutable production-corpus plan, evidence-derived foundation and residual-E0 qualification, numerical replay-label identity, content-addressed DATA8 generation promotion, self-verifying loaders, and generic optional-extension gate requirements. DATA9B1 in 0.20.56a0 adds passed-gate campaign-matrix freezing, protocol-family and seed-variant identities, content-addressed checkpoint catalogs, external metric records, deterministic hard-constraint admissibility, and fail-closed checkpoint selection. DATA9B2 in 0.20.57a0 adds supervised/restartable MACE execution, automatic target/replay checkpoint evaluation, fold/seed aggregation, learning curves, deterministic protocol comparison, target-head committee export, protocol freeze, and sealed-evaluation activation. DATA9B3 in 0.20.58a0 adds the unified source-checkout campaign CLI, one-database orchestration state, manifest approval, production preparation/training/evaluation commands, source-local precision-wrapper shims, and bounded NVE deployment verification. DATA9B3A in 0.20.59a0 makes the MACE acceleration backend a frozen campaign policy, auto-selects cuEquivariance at initialization when qualified, and propagates it through DATA6, DATA8, preflight, production training, checkpoint evaluation, and bounded verification without silent fallback. DATA2A in 0.20.60a0 adds XML-backed review-manifest metadata, percentage-aware filename strain candidates, exact LTA fixed-cell geometry verification, and fail-safe promotion before manual manifest approval. DATA2 interrupted-stream hardening in 0.20.61a0 adds EOF-qualified interrupted `vasprun.xml` recovery across ENS0, DATA2 source audit, and normalized trajectory loading while preserving strict rejection of ambiguous or mid-file corruption.
The post-0.20.105 evaluation/storage cycle implements EVAL-MF1 in 0.20.106a0 and EVAL-MF2 in 0.20.107a0: deterministic nested equal-fraction target/replay checkpoint screening, delta-only prediction reuse, conservative source/block-aware survivor guards, comprehensive epoch reporting, and full-fidelity finalist publication are now the generated production evaluation strategy.
The post-0.20.120 adaptive-training revision was recorded as architecture-only planning in 0.20.121a0. **ADAPT-PREC1 is implemented in 0.20.122a0**, **ADAPT-MON1 in 0.20.123a0**, **ADAPT-STOP1 in 0.20.124a0**, **ADAPT-RANK1 in 0.20.125a0**, **ADAPT-EVAL1 in 0.20.126a0**, **ADAPT-VERIFY1 in 0.20.127a0**, and **ADAPT-MIGRATE1 in 0.20.128a0**: new campaigns use binary `single|double` learned-model precision, fixed common target/true-replay online monitors, criterion-driven epoch termination, zero-new-inference one-champion-per-run screening, top-K authoritative full evaluation, score-ordered bounded verification with deterministic fallback, and schema-aware migration/storage authority. Only the first verification-passing target-head artifact is published. EVAL-MF and historical committee workflows remain readable but are no longer the generated adaptive production path. The seven-gate adaptive revision is complete. A conventional-CV correction roadmap was recorded in `0.20.130a0`. **MLCV-ROLE1 is implemented in `0.20.131a0`**, **MLCV-MON1 in `0.20.132a0`**, **MLCV-STOP1 in `0.20.133a0`**, **MLCV-RANK1 in `0.20.134a0`**, **MLCV-SELECT1 in `0.20.135a0`**, **MLCV-AGG1 in `0.20.136a0`**, **MLCV-FINAL1 in `0.20.137a0`**, **MLCV-VERIFY1 in `0.20.138a0`**, and **MLCV-MIGRATE1 in `0.20.139a0`**. DATA5 roles now have typed immutable authority/lineage; new preparations materialize role-correct fold/final/replay monitors and selection-inert training diagnostics; adaptive stopping uses configurable derived lightweight control margins without lightweight full-threshold rejection; each run retains up to five finite lightweight-ranked checkpoints; those candidates are fully screened on the run-correct `V_i_full`/`D_full` plus complete TRUE_DFT `R_full` before exactly one representative (or explicit failure) is frozen; frozen fold representatives are evaluated once on untouched outer folds for conventional per-seed CV robustness evidence; and only qualified full-development representatives enter final-seed comparison and committee export. VERIFY1 owns qualified-final-seed physical fallback, one-shot locked-test activation, and verified production publication. MIGRATE1 now binds conventional-CV campaigns to the distinct `mlcv_nested_cv` lifecycle authority and protects the complete MLCV evidence graph. **mdstats 0.20.140a0 corrects replay retention semantics end-to-end:** target error remains absolute, while replay acceptance/scoring is foundation-relative degradation with matched `R0_light`/`R0_full` baselines. Historical absolute-replay evidence remains readable under its original schema/digest; replay-dependent transitional evidence is explicitly stale and is never silently reinterpreted. The nine-gate conventional-CV architecture remains complete with this versioned semantic correction.

**PERF-BASE0/P0/P1, SIZE-HALVE1, SIZE-FIDELITY1 authority, PERF-P2R CPU/control-plane execution, PERF-P3 CPU hardening, VRAM1/PERF-P4 CPU/control-plane execution, PERF-P5 late persistence hardening, and the CUEQ-DEP1 runtime-freeze control plane are implemented through `mdstats 0.20.188a0`.** PERF-BASE0 freezes the supplied-data numerical/performance oracle; PERF-P0/P1 provide native exact coverage/selection state; SIZE-HALVE1 corrects target-size screening to hard coverage followed by a 3/10/30 learning funnel; and SIZE-FIDELITY1 implements exhaustive retrospective calibration of that low-fidelity screen. `0.20.184a0` re-anchors the supplied MACE-MH-1 and MACE-MPA-0-medium files and adopts `FINAL-GPU1`, deferring all remaining MLFF GPU-dependent qualification to one final-release workstation run. `0.20.185a0` removes remaining DATA6 local-structure wrapper/allocation overhead and adds fail-closed CPU/thread budgets. `0.20.186a0` corrects DATA6 capacity evidence to the actual combined workload and implements bounded graph/inference/persistence orchestration with an exact synchronous fallback. `0.20.187a0` hardens TRAIN2/STOR2 hashing and EVAL2 reconstruction. `0.20.188a0` adds content-addressed CuEq core/Torch/CUDA-ops dependency evidence, CUDA/determinism provenance, and FINAL-GPU1 preflight schema v2. **CUEQ-DEP1 implementation is complete, but its positive accelerator record and every later CuEq numerical/training gate remain deferred to `FINAL-GPU1`.** Pending GPU evidence may not be converted into scientific defaults or accelerator-performance claims.

The central architectural rule is:

> Source facts, eligibility decisions, statistical partitions, training
> selections, epoch exposures, and active-learning acquisitions are distinct
> immutable records. No record is allowed to silently assume the role of
> another.

The architecture makes the following binding decisions.

1. Cross-validation uses independent training jobs. A continuously evolving
   model never rotates a previously trained-on fold into a validation role.
2. Every fold has a checkpoint monitor distinct from its gradient-training and
   held-out evaluation domains. The evaluation fold never selects a checkpoint.
3. Outer monitor validation, final-committee calibration, and locked tests are
   separate evidence domains with explicit feasibility and independence grades.
4. Feature transforms, fitted feature metrics, atomic-reference fits, and
   training selection are fitted separately inside every cross-validation fold.
5. Partition-critical features and events are supplied by the declared material
   profile before the outer partition is locked. LTA ring/site states are one
   optional porous/zeolite extension, not a core dependency.
6. The first MACE export supports exactly one target electronic-structure label
   domain per development bundle, plus an optional replay head.
7. Locked tests are sealed outside training configurations and are activated
   only after a `ProtocolFreezeRecord` identifies the complete frozen protocol
   and selected model committee.
8. Atomic-reference structural identifiability is audited before partitioning;
   numerical E0 corrections are fit only on the applicable training domain and
   are serialized as explicit elemental mappings.
9. Source occurrence, physical geometry, and label payload have separate
   identities.
10. Events are detected before ordinary temporal thinning.
11. Nested training sizes are prefixes of one deterministic, quota-interleaved
    master order under explicit `FeatureMetricPolicyTemplate`, fitted metric,
    and `SelectionBudgetPolicy` records.
12. Training membership, loss weighting, epoch exposure, and replay balancing
    are separate policies. The realized MACE loader exposure is audited rather
    than inferred from exported file counts.
13. Cross-validation is bound to a complete `TrainingProtocolIdentity`, including
    foundation checkpoint, replay mode, objective, exposure backend, and
    checkpoint-control policy. Results from naive and replay fine-tuning are not
    interchangeable.
14. Replay retention constrains checkpoint selection. The initial MACE adapter
    saves candidate checkpoints, verifies target-monitor control of native
    scheduling, and applies the replay constraint through an external,
    deterministic checkpoint audit [17, 18].
15. The first adapter supports native fixed-file MACE training only. Dynamic
    epoch resampling requires a later custom loader or explicit multi-job
    protocol and is never represented as an artifact-only feature.
16. Numerical active-learning thresholds are calibrated using the actual final
    committee and a dedicated calibration cohort. Calibration has a declared
    applicability domain; outside it, acquisition is rank-only until
    recalibration.
17. Label-derived difficulty features are training-domain private. Locked
    validation, calibration, and test residuals remain blinded until their
    authorized evaluation stage.
18. Active-learning candidates have a pre-DFT admissibility contract distinct
    from post-DFT labeled-frame eligibility, and child datasets inherit existing
    roles unchanged by default.
19. The MACE adapter is version-locked and tested at implementation time. The
    initial baseline is `mace-torch==0.3.16`; exact CLI and source contracts are
    captured in every generated bundle [9, 10, 17, 18].
# Reader orientation

## What an MLFF learns

An energy-conserving machine-learned force field represents a potential-energy
function

$$
E_\theta = E_\theta(\mathbf Z, \mathbf R, \mathbf H),
$$

where $\mathbf Z$ contains atomic numbers, $\mathbf R$ contains positions,
$\mathbf H$ is the periodic cell, and $\theta$ denotes model parameters.
Forces and stress follow from derivatives of the same energy:

$$
\mathbf F_i = -\frac{\partial E_\theta}{\partial \mathbf R_i},
\qquad
\boldsymbol\sigma = -\frac{1}{V}
\frac{\partial E_\theta}{\partial \boldsymbol\epsilon},
$$

up to the exact stress sign and strain convention declared by the label source.
MACE builds symmetry-aware local atomic features and sums atomic energy
contributions [1]. A useful dataset therefore has to constrain both the energy
surface and its derivatives throughout the intended simulation domain.

A low average force error is not sufficient. A model can fit common framework
vibrations while failing on rare mobile-ion environments, strained cells, or
migration geometries. Validation must include both numerical errors and
physically relevant observables [6].

## Why adjacent MD frames are not independent

A molecular-dynamics trajectory contains temporally correlated configurations.
At a 1 fs output interval, neighboring frames are often nearly duplicates.
Using them in different statistical roles creates leakage and overstates model
accuracy.

For an observable $x_t$, the normalized autocorrelation at lag $k$ is

$$
\rho_x(k) =
\frac{
\langle (x_t-\bar x)(x_{t+k}-\bar x)\rangle
}{
\langle (x_t-\bar x)^2\rangle
}.
$$

A truncated integrated autocorrelation time is

$$
\tau_{\mathrm{int},x}
=
\Delta t
\left[
\frac{1}{2}+
\sum_{k=1}^{k^\star}\rho_x(k)
\right].
$$

The effective number of independent observations is approximately

$$
N_{\mathrm{eff},x}
\approx
\frac{T}{2\tau_{\mathrm{int},x}}.
$$

Block averaging and hv-block cross-validation provide established foundations
for handling correlated data [3-5]. The branch uses these ideas but records the
mdstats-specific estimator, truncation rule, minimum block size, and purge rule
as explicit policies.

## The three ordinary dataset roles

| Role | Function | May affect parameters? | May affect model choice? |
|---|---|---:|---:|
| Training | Supplies gradient updates | Yes | Yes |
| Validation | Early stopping and hyperparameter choice | No | Yes |
| Test | Final locked evaluation | No | No |

MACE documents the same distinction: validation controls early stopping, while
the test set is independent and evaluated at the end [8].

The architecture adds two more evidence roles:

| Role | Function |
|---|---|
| Calibration | Calibrates committee disagreement or acquisition thresholds |
| Challenge test | Evaluates a named extrapolation or physical mechanism |

Calibration is not test data. Challenge tests are not ordinary validation data.

## REPLAY-UNIFY1B implementation boundary

Revision 78 implements the source-true-label layer without changing live TRAIN2/DATA8 replay execution. `ReplayTrueLabelCache` binds the canonical geometry -> source-label identity mapping from `ReplaySourceArtifact`; the logical cache is independent of ExtXYZ ordering and locator, while materialization still verifies the authenticated source SHA before reconstructing a missing transport view. Missing energy/forces are inventoried rather than hidden, and any requested role containing incomplete truth fails closed. Stress remains optional and is preserved when present.

`ReplayTrueLabelViewArtifact` is the authenticated transport receipt for a lazily generated `train` or `monitor` source-truth view. Its stable `logical_digest` binds the role, exact split-manifest authority, geometry-set identity, true-label-set identity, and true-label-cache identity while excluding path and transport byte ordering. Its `content_digest` additionally authenticates the generated ExtXYZ SHA-256. `REF_energy`, `REF_forces`, and optional `REF_stress` are emitted only at this transport boundary; pseudo-label metadata is removed and source truth remains logically independent.

`materialize_replay_true_label_views()` accepts either role independently. If both requested outputs are absent/stale, mdstats streams the single replay source once and routes frames to bounded ExtXYZ buffers for both roles; it does not parse the source twice. If an authenticated view already exists, its receipt and output SHA are validated and returned without opening the replay source. Deleting a materialized file causes deterministic reconstruction only; no foundation-model inference exists in this gate. A source/cache pair with identical geometry authority but different source-label mapping is rejected before any cache hit or write.

The supplied `LTA_replay/mp_replay_selected.extxyz` provides direct Gate-B evidence: 12,000 configurations, 12,000 complete finite source energy/force label pairs, stress on all 12,000 frames, and the default split manifest yields exactly 10,000 train plus 2,000 monitor. On the development CPU host, source inspection required approximately 9.4 s, a cold monitor-only materialization including inspection required approximately 15.8 s, and cold dual-role 10,000+2,000 materialization including inspection required approximately 20.3 s with about 278 MB peak RSS. An authenticated dual-role cache hit returned in approximately 0.23 s without source parsing. These measurements are implementation evidence, not cross-machine performance promises.

A profiling pass found and removed an accidental quadratic hot path: immutable 12,000-entry cache/split digests were initially recomputed for every selected frame. Gate B freezes the corrected rule that whole-corpus digests and label mappings are constructed once per materialization call and reused per frame. This is part of the optimization contract carried into REPLAY-UNIFY1E.

**REPLAY-UNIFY1B acceptance:** source truth is never overwritten internally; requested view geometry membership equals the immutable split role; train and monitor remain disjoint; missing requested truth fails closed; same-geometry/different-label cache masquerading fails; dual-role cold generation uses one source pass; authenticated cache hits use zero source parses; deleted views reconstruct without pseudo inference; legacy true-label materialization APIs and production replay execution remain unchanged.

**Gate B successor:** REPLAY-UNIFY1C is implemented in Revision 79.

## REPLAY-UNIFY1C implementation boundary

Revision 79 implements the foundation pseudo-label layer without changing live TRAIN2/DATA8 replay execution. `ReplayFoundationPredictionPolicy` binds `FoundationPotentialIdentity` plus `FoundationInferenceIdentity` and an explicit execution device. The policy rejects unresolved CuEq, backend/kernel disagreement, checkpoint/head/dtype mismatch, and unsupported source species. Batch size and physical shard size are intentionally excluded from scientific prediction identity so performance tuning cannot invalidate numerically identical replay authority.

`ReplayFoundationPredictionCache` stores bounded ragged energy/force/stress shards while its logical digest is independent of source ordering, cache location, and shard grouping. Each geometry binds a prediction-label identity and an audit identity. Before provider execution, mdstats copies each geometry and removes source `energy/forces/stress` and calculator results; source truth therefore remains an independent namespace and cannot enter the foundation prediction graph. The default provider path reuses the existing optimized `MaceCalculatorProvider.predict_batch()` implementation, including native graph batching and bounded OOM backoff; no new one-frame calculator loop is authoritative.

Qualification uses a separate authenticated `mdstats.replay-foundation-audit-cache.v1` sidecar containing only geometry identity, force-component RMS, maximum atomic-force norm, maximum absolute stress, and audit identity. `ReplayPseudolabelQualificationPolicy` defaults to the historical replay preparation thresholds of 20 eV/Angstrom maximum force, 5 eV/Angstrom force-component RMS, and 0.5 eV/Angstrom^3 maximum absolute stress, with optional required stress. Threshold changes rebuild only `ReplayPseudolabelQualification`; they perform zero model calls and do not read ragged force/stress prediction shards.

`materialize_replay_pseudolabel_views()` is qualification- and split-manifest-bound. It writes only requested train/monitor transport views, assigns foundation predictions to `REF_energy`, `REF_forces`, and optional `REF_stress`, and records model SHA, resolved foundation head, foundation-inference digest, prediction-cache digest, qualification digest, and split digest. Existing authenticated views return without source parsing or prediction-shard access. A deleted view reopens the source and prediction cache only; it never reruns the foundation model. Audit-sidecar tampering fails at qualification, and ragged prediction-shard tampering fails when a pseudo-label transport needs those predictions.

On the supplied 12,000-configuration LTA source, a deterministic non-MACE provider was used strictly for development-host control-plane qualification. The pipeline generated 47 prediction shards from 188 batches, classified all 12,000 as eligible, and reproduced exactly 10,000 train plus 2,000 monitor configurations. After separating the compact audit sidecar, qualification measured approximately 0.13 s and a subsequent threshold-only reclassification approximately 0.11 s; dual-role pseudo-label materialization measured approximately 9.34 s; an authenticated dual-role view hit approximately 0.22 s; peak RSS was approximately 280 MB. These measurements validate algorithmic/control-plane scaling only and are not MACE throughput or numerical-parity evidence. Real CUDA/CuEq replay inference remains deferred to the final regenerated FINAL-GPU1 package.

**REPLAY-UNIFY1C acceptance:** model/head/runtime changes select a distinct prediction authority; batch/shard tuning does not; source-order rewrites preserve logical prediction identity; threshold-only reclassification performs zero inference and reads only the compact audit cache; source truth is not overwritten or exposed to provider input; pseudo-label views are lazy and exact split subsets; cached-view restart performs zero source parses/model calls; deleted views reconstruct without reinference; cache/audit corruption fails closed; legacy replay execution remains unchanged.

**Gate C successor:** REPLAY-UNIFY1D is implemented in Revision 80.

## REPLAY-UNIFY1D implementation boundary

Revision 80 switches the campaign-facing replay authority from externally supplied split files to the single selected `[paths].replay_set`. New `mdstats mlff campaign init` output contains only `replay_set`; the historical `replay_train`, `replay_monitor`, and `replay_true_labels` command-line inputs remain hidden compatibility inputs and are never emitted by a new-style configuration. New and legacy replay inputs cannot be mixed.

The integration deliberately uses an adapter boundary rather than rewriting TRAIN2/DATA8 scientific schemas in the same gate. `_single_source_replay_context()` reconstructs or prepares the authoritative Gate-A/B/C records, then emits disposable internal train/monitor ExtXYZ transport views below `.mdstats/replay-unified/views`. Those outputs are re-described as historical `ReplayFileArtifact` objects solely for downstream compatibility; their paths and bytes are not external replay authority. A SHA-bound sidecar receipt prevents repeated 10k/2k artifact rescans.

For `true_dft`, the immutable split is bound to the true-label-cache authority and both source-truth roles can be generated in one pass. For `foundation_pseudolabel`, the prediction policy binds the doctor-frozen foundation model/head/inference/runtime realization, `prepare` builds or reuses the Gate-C prediction/audit cache, qualification freezes the eligible geometry set, and the resulting split materializes pseudo-label train/monitor plus an independent true-label monitor on identical geometry membership. If a caller later requires true-label train data, that role is materialized lazily from the same source/cache/split. No pseudo-label output overwrites source truth.

`doctor` performs cheap structural and true-label validation of `replay_set` plus acceleration/runtime qualification, but does not execute a full 12,000-frame foundation prediction pass. `prepare` is the first stage permitted to pay that cost, and it persists all replay authorities into the campaign store. Prepare/restart receipts now bind single-source config, replay source, true-label cache, prediction policy/cache, pseudo-label qualification, split manifest, and materialized-view records when present. A persisted `mdstats.replay-source-artifact-receipt.v1` avoids source ExtXYZ reparsing across process restarts when SHA and locator still match.

Generated configuration defaults remain `split_ratio = "5:1"` and `split_seed = 42`; for a fully qualified 12,000-frame source this yields exactly 10,000 train plus 2,000 monitor. Storage accounting protects `replay_set` as the single external replay input. Legacy split-file campaigns remain readable, but their paths are deprecated and omitted from public init help.

The supplied 12,000-frame LTA replay source qualified the new campaign-facing `true_dft` integration path directly: cold plan construction produced 10,000/2,000 internal views in approximately 27.6 s with about 336 MB peak RSS, while a process-style restart after clearing the in-memory context returned in approximately 0.60 s without replay-source reparsing. Pseudo-label campaign integration is covered by deterministic provider tests in this gate; real MACE/CUDA/CuEq execution remains deferred to FINAL-GPU1 after Gate E.

**REPLAY-UNIFY1D acceptance:** new configs expose only `replay_set`; mixed interfaces fail closed; true and pseudo campaigns derive internal train/monitor artifacts from one source; pseudo train/monitor and independent true monitor share exactly the same split geometry authority; doctor defers full pseudo inference; prepare persists complete replay authority; restart receipts include single-source records; process-style restart reuses the authenticated source receipt; legacy configs remain readable; downstream TRAIN2/DATA8 contracts remain scientifically unchanged through the adapter boundary.

**Next implementation gate:** `REPLAY-UNIFY1E` - migration hardening, invalidation-matrix and performance qualification, cleanup of legacy-facing documentation, and regenerated consolidated FINAL-GPU1 handoff.

# Scope

## Included

The branch will provide:

- VASP trajectory discovery and source certification;
- composition, temperature, ensemble, and strain reconstruction;
- electronic-structure compatibility and label-domain classification;
- energy, force, and stress label auditing;
- atomic-reference-energy identifiability diagnostics;
- frame-level eligibility and quality decisions;
- generic physical feature providers plus optional material-profile extensions;

LTA is an optional profile extension; it is not the generic feature or selection default.

- optional MPA-0 descriptors and zero-shot residuals;
- event detection before ordinary thinning;
- autocorrelation-aware complete-frame blocks;
- fixed outer validation, calibration, and locked test domains;
- independent cross-validation job families;
- fold-local transformations and training selection;
- deterministic nested training-size ladders;
- MACE target/replay artifact generation;
- replay-retention monitoring;
- training-only epoch resampling and exposure accounting;
- active-learning candidate screening, acquisition, and immutable lineage.

## Excluded from the first runtime release

The first runtime sequence will not:

- patch the internal MACE optimizer or data loader;
- claim that coverage metrics prove final MLFF accuracy;
- infer an unstrained reference cell when more than one reference is defensible;
- merge incompatible DFT levels into one target head;
- use locked test labels for uncertainty calibration;
- treat replay-head disagreement as an uncertainty committee;
- silently download replay data from the mdstats core;
- promise efficient random access to XML before a streaming/indexed reader exists.

# Reference application: bulk Li/Na/K-LTA

The first scientific target contains 27 AIMD runs:

- seven cation compositions: Li, Na, K, LiNa, NaK, LiK, and LiNaK;
- three temperatures: 300, 700, and 800 K;
- six additional LiNaK strain runs: hydrostatic $\pm5\%$ volume,
  constant-volume orthorhombic $\pm2\%$ linear strain, and engineering shear
  $\pm2\%$;
- 1.4 ps per run at 1 fs time step;
- a Langevin NVT protocol, with approximately 0.2 ps initial relaxation.

This dataset motivates several domain-specific requirements:

1. Framework atoms greatly outnumber mobile cations. Global descriptor averages
   must not hide Li, Na, or K environments.
2. Strain combinations do not form a full Cartesian product with composition
   and temperature. Stratification must be hierarchical.
3. One trajectory per condition provides temporal interpolation evidence, not a
   fully independent replica test.
4. Fixed framework stoichiometry makes individual atomic reference-energy
   corrections non-identifiable without additional anchors.
5. Short trajectories may contain few cation hops. Absence of a transition is a
   documented coverage gap, not evidence that the transition is unimportant.

# Relationship to existing mdstats capabilities

The training-data branch is an orchestrator over existing mdstats scientific
capabilities.

| Existing capability | Reused evidence |
|---|---|
| `mdstats.io.vasp.read_vasp_frames` | cells, coordinates, energies, forces, stress, temperature, provenance |
| `mdstats.io.vasp_controls.read_vasp_run_controls` | source controls, named energy channels, SCF iterations |
| `mdstats.io.vasp_ensemble.certify_vasp_simulation_controls` | NVE/NVT/NpT/NpH and driven-control classification |
| `mdstats.io.trajectory_quality.assess_trajectory_quality` | source and trajectory integrity verdicts |
| `mdstats.io.production_regimes.assess_production_regimes` | transient and stationary regime evidence |
| Stage 11 structural modules | LTA rings, sites, coordination, topology, transitions |
| `mdstats.io.sampling_crossfit` | design precedent for source-bound blocks and purge semantics |

The new branch owns dataset-level comparison, partition, selection, export, and
active-learning lineage. It does not redefine the underlying physical analyses.

# Controlling data flow

The controlling flow is:

```text
source bytes
  -> source occurrence identity
  -> VASP controls + trajectory collection
  -> ensemble, quality, and production-regime evidence
  -> source catalog + decomposed label-domain audit
  -> structural atomic-reference identifiability
  -> immutable frame facts
       occurrence UID
       geometry fingerprint
       label payload digest
       labeled-configuration fingerprint
  -> labeled-frame eligibility
  -> full-resolution generic + partition-critical profile features
  -> event detection before ordinary thinning
  -> complete-frame temporal blocks
  -> fixed outer partition + PartitionIndependenceReport
       development pool
       outer monitor validation
       dedicated final-committee calibration cohort
       locked interpolation test
       named locked challenge tests
  -> independent cross-validation job family
       fold-training domain
       nested fold checkpoint monitor
       held-out evaluation fold
       fold-local feature metric + transform
       fold-local atomic-reference fit
       fold-local selection
       fresh model and frozen checkpoint per fold
       out-of-fold predictions
  -> final target-training transform + E0 fit + deterministic master order
  -> nested training-size ladder
  -> development MACE target/replay bundle
       no locked-test path
       replay-retention checkpoint constraint
  -> selected final checkpoints + independent-seed committee
  -> final-committee predictions on dedicated calibration cohort
  -> committee-bound uncertainty calibration
  -> post-freeze locked evaluation bundle
  -> active-learning candidate trajectories
  -> candidate admissibility + novelty + calibrated or rank-only uncertainty
  -> DFT query manifest
  -> labeled-round eligibility
  -> append-only child dataset generation with inherited roles
```

No arrow runs from a locked test into a fitted transform, E0 fit,
hyperparameter or checkpoint choice, uncertainty calibration, or acquisition
rule.

# Package and ownership structure

```text
mdstats/
  sampling/
    autocorrelation.py
    blocks.py
    assignment.py

  training_data/
    __init__.py
    policies.py
    records.py
    sources.py
    label_domains.py
    reference_energies.py
    conditions.py
    strain.py
    identity.py
    eligibility.py
    frame_catalog.py
    events.py
    independence.py
    partition_feasibility.py
    feature_metric.py
    blinding.py
    features/
      base.py
      thermodynamic.py
      geometry.py
      coordination.py
      lta.py
      mace.py
    partition.py
    cross_validation.py
    training_protocol.py
    objectives.py
    checkpoint_selection.py
    selection.py
    exposure.py
    replay.py
    replay_retention.py
    calibration.py
    active_learning.py
    role_inheritance.py
    export/
      extxyz.py
      mace.py
      manifest.py
    workflow.py
```

The proposed `mdstats.sampling` package contains source-independent primitives.
Existing Stage 11 public records remain unchanged and may be reimplemented
internally over these primitives only after exact replay tests pass.

# Evidence records and immutability

## Source facts

`TrainingDataSource` records facts derived from one source occurrence:

```text
run_id
source_path
source_sha256
source_identity_signature
composition
timestep
frame_count
ensemble_certificate
quality_signature
production_regime_signature
label_domain_id
reference_group
```

## Frame facts

`TrainingFrameRecord` contains only source-derived, policy-independent facts:

```text
frame_uid
source_identity_signature
source_occurrence_signature
source_frame_index
time
atomic numbers
cell reference
label references
condition references
geometry_fingerprint
label_payload_digest
labeled_configuration_fingerprint
```

It does **not** contain eligibility, partition, selection, exposure, or
acquisition state. The three fingerprints have different purposes and remain
separate fields.

## Decision records

Separate records are keyed by `frame_uid` or by an explicit dataset/job identity:

```text
FrameEligibilityDecision
PartitionAssignment
SelectionAssignment
ExposureAssignment
CandidateAdmissibilityDecision
AcquisitionDecision
```

A new policy produces new decision records without mutating frame facts.

## Workflow-policy and fitted records

The architecture also separates static policy templates from data-fitted or
runtime-realized products:

```text
PartitionRoleBudgetPolicy
PartitionFeasibilityReport
FeatureMetricPolicyTemplate
FoldFeatureMetricFit
FinalFeatureMetricFit
SelectionBudgetPolicy
TrainingObjectivePolicy
ConfigurationWeightPolicy
PropertyWeightPolicy
CheckpointMetricPolicy
TrainingProtocolIdentity
MaceCheckpointControlPolicy
ExposureBackendPolicy
MaceExposureRealizationRecord
ReplayRetentionPolicy
ProtocolFreezeRecord
CalibrationApplicabilityDomain
CalibrationTransferDecision
```

A policy template specifies an algorithm and fixed choices. A fitted record
contains parameters learned from one declared training domain. A realization
record contains behavior actually observed from an external tool. These roles
are not interchangeable.

## Content digests, not digital signatures

Previous documents used the word "signed" for deterministic record hashes. This
manual uses precise terms:

- `content_digest`: canonical hash of one record;
- `policy_digest`: canonical hash of a policy;
- `source_digest`: hash of source bytes;
- `cryptographic_signature`: optional authenticated signature, not required in
  the first release.

A content digest detects modification but does not authenticate the author.

# Source and manifest contract

## Dataset manifest

A YAML or JSON manifest supplies source paths and information that cannot be
reliably reconstructed from a single `vasprun.xml`:

```yaml
dataset_id: bulk-lta-initial
system_profile: lta

runs:
  - run_id: Li_300K
    vasprun: raw/Li_300K/vasprun.xml
    reference_group: Li_bulk
    replica_id: seed001

  - run_id: LiNaK_hydro_plus_005
    vasprun: raw/LiNaK_hydro_plus_005/vasprun.xml
    reference_group: LiNaK_bulk
    reference_run_id: LiNaK_700K
    assertions:
      intended_strain_class: hydrostatic
      intended_volume_change: 0.05
```

Manifest values are either:

- source locators;
- grouping declarations;
- scientific assertions to verify;
- explicit expert overrides with rationale.

A directory name is never treated as a physical label without verification.

## Occurrence, geometry, and label identities

### Source-occurrence identity

The DATA2 `source_identity_signature` is content-derived and may therefore be
shared by byte-identical copied sources. DATA3 first binds that identity to one
manifest occurrence:

$$
\mathrm{source\_occurrence\_signature}
=
\operatorname{SHA256}
(
\mathrm{run\_id},
\mathrm{source\_locator},
\mathrm{source\_identity\_signature}
).
$$

The frame occurrence is then

$$
\mathrm{frame\_uid}
=
\operatorname{SHA256}
(
\mathrm{source\_occurrence\_signature},
\mathrm{source\_frame\_index}
).
$$

This identity is stable under later concatenation and export, while two copied
sources declared as distinct manifest runs intentionally receive different
occurrence identities.

### Source-independent geometry fingerprint

`geometry_fingerprint` identifies the atomic geometry independently of labels.
The first implementation supports exact copy/restart overlap detection using:

- ordered atomic numbers;
- canonical wrapped fractional coordinates;
- canonical cell representation;
- explicit numerical tolerances.

Energy and forces are deliberately excluded. The same geometry evaluated at a
different DFT level or convergence threshold must still be detectable as the
same geometry.

### Label payload digest

`label_payload_digest` hashes the selected energy, forces, stress or virial,
label-domain identity, and their declared numerical representation. It detects
whether two occurrences carry the same labeled payload.

### Labeled-configuration fingerprint

`labeled_configuration_fingerprint` combines the geometry fingerprint and label
payload digest. It answers the narrower question: "is this the same geometry
with the same labels?"

Leakage audits use all of the following:

- exact `frame_uid` overlap;
- exact geometry-fingerprint overlap;
- exact labeled-configuration overlap;
- near-geometry or descriptor distance;
- forbidden temporal proximity.

Later revisions may add permutation-, basis-, and symmetry-aware approximate
geometry matching without changing these identity roles.

# Electronic-structure label domains

## Why the fingerprint is decomposed

Electronic-structure settings do not all have the same meaning. The architecture separates five records.

### `TheoryIdentity`

Examples:

- exchange-correlation functional;
- DFT+U form and parameters;
- pseudopotential or PAW datasets;
- spin formalism;
- dispersion or hybrid-functional settings.

### `EnergyReferenceIdentity`

Examples:

- energy channel;
- smearing/free-energy convention;
- atomic reference convention;
- per-cell versus per-atom normalization.

### `DerivativeConvention`

Examples:

- force sign and units;
- stress versus virial;
- stress sign;
- tensor/Voigt representation;
- shear convention.

### `NumericalQualityProfile`

Examples:

- ENCUT;
- k-point density;
- EDIFF;
- PREC;
- LREAL;
- LASPH;
- SCF iteration behavior.

### `SoftwareProvenance`

Examples:

- VASP version;
- parser version;
- POTCAR hashes;
- source-control reconstruction version.

A versioned `LabelCompatibilityPolicy` determines whether differences are:

```text
compatible
compatible_with_quality_flag
separate_label_domain
unresolved
```

Exact equality of the complete fingerprint is not required, but theory- or
reference-defining differences cannot be waived silently.

## First-release MACE rule

One MACE bundle contains exactly one target `LabelDomain` and optionally one
foundation replay head. If the dataset contains two incompatible target DFT
levels, mdstats produces two target bundles.

General arbitrary multi-target-head export is deferred until a later MACE
adapter revision. This restriction makes the initial data contract unambiguous
while preserving a path to MACE's general multi-head capability [11, 12].

## Energy-channel policy

VASP forces and stress are derivatives of the electronic free-energy surface at
the chosen electronic smearing. The selected `REF_energy` must therefore be an
explicit named channel consistent with the derivative labels [7].

Example:

```python
VaspEnergyLabelPolicy(
    channel="e_fr_energy",
    require_complete=True,
    derivative_consistency="electronic_free_energy",
)
```

The exact channel, units, completeness, and provenance are exported.

# Atomic reference-energy audit and fitting

MACE commonly writes the total energy as

$$
E = \sum_i E_{0,Z_i} + E_{\mathrm{interaction}}.
$$

When foundation-model corrections are estimated, one solves a system of the
form

$$
\mathbf A\,\Delta\mathbf e_0 \approx \mathbf b,
$$

where $A_{cZ}$ is the count of element $Z$ in configuration $c$, and $b_c$ is
the target-minus-foundation energy residual. Current MACE uses a least-squares
solution, reports matrix rank, and warns when the element-count system is rank
deficient [10].

The architecture separates two operations that have different leakage rules.

## Structural identifiability audit

`AtomicReferenceIdentifiabilityReport` depends only on elemental count vectors
and an atomic-reference policy. It may be created before partitioning and
contains:

```text
element order
count matrix shape
rank
singular values
condition number
null-space dimension
identifiable linear combinations
policy outcome
transfer limitations
```

It does **not** contain fitted elemental corrections or a fit residual.

Allowed structural outcomes are:

```text
identified
rank_deficient_but_fixed_domain_usable
user_supplied
isolated_atom_anchored
foundation_preserved
rejected
```

For fixed-stoichiometry LTA, individual Si, Al, and O corrections are not all
identifiable. A rank-deficient system may still be accepted for the same fixed
stoichiometric manifold, but its null space and transfer restrictions must be
explicit.

## Training-domain atomic-reference fit

`AtomicReferenceFitRecord` is a fitted object. It contains:

```text
training-domain frame UIDs
element support by element
structural-identifiability report digest
foundation-checkpoint digest
fitted elemental corrections
least-squares residual
solver and numerical tolerance
policy outcome
```

It may inspect only the applicable target-training domain:

- each cross-validation job has a separate fold-local fit;
- the final production run has a separate final-training fit;
- outer monitor, calibration, held-out fold, and locked-test labels are excluded.

Before fitting, every required element must have sufficient support in that
training domain. Missing-element or newly rank-deficient fold fits fail or use
an explicitly declared alternative such as user-supplied or foundation-preserved
references.

`E0s: estimated` is emitted only when the corresponding training-domain fit is
accepted. The bundle must state that rank-deficient offsets are not transferable
to a different Si/Al ratio, defect count, cation count, salt phase, or interface.

# Ensemble, temperature, and strain

## Ensemble

The branch consumes the existing mdstats control certificate. It distinguishes
at least:

```text
NVE
NVT
NpT
NpH
temperature ramp
constant-velocity path
driven nonequilibrium
multi-thermostat
unresolved
```

Ensemble is not inferred merely from observed cell variation.

## Temperature

A `TemperatureCondition` stores:

- requested `TEBEG` and `TEEND`;
- thermostat target;
- instantaneous ionic temperature series;
- production-regime mean and uncertainty;
- drift and stationarity diagnostics;
- ramp status.

Nominal and realized temperature remain separate.

## Reference-cell resolution

Strain requires an explicit reference. The resolution order is:

1. explicit cell matrix;
2. explicit reference structure;
3. explicit reference run;
4. a unique compatible unstrained run in the same reference group;
5. unresolved.

Ambiguity fails closed.

## Strain tensor

The cell-matrix convention is normative. ASE stores the three lattice vectors
as **rows** of `Cell.array`. Fractional row vectors map to Cartesian row vectors
as

$$
\mathbf r_{\mathrm{row}} = \mathbf s_{\mathrm{row}}\mathbf H.
$$

For reference cell $\mathbf H_0$ and current cell $\mathbf H_t$, the deformation
gradient acting on Cartesian **column** vectors is

$$
\mathbf F_t = \left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

Equivalently, a row-vector implementation may use the right-acting map
$\mathbf H_0^{-1}\mathbf H_t$ provided that all reported tensors are converted
to the declared Cartesian-column convention before serialization. Use the right
polar decomposition

$$
\mathbf F_t = \mathbf R_t\mathbf U_t
$$

to separate rotation from stretch. Record:

- volume ratio;
- linearized strain;
- Green-Lagrange strain;
- logarithmic strain;
- hydrostatic component;
- deviatoric norm;
- principal strains;
- tensor shear;
- engineering-shear equivalent;
- rotation;
- storage convention and coordinate frame.

Classifications are:

```text
unstrained
hydrostatic
orthorhombic_or_deviatoric
shear
mixed_strain
variable_cell_fluctuation
unresolved
```

The fixture suite must include a nonsymmetric shear and a rotated stretch.
Hydrostatic and diagonal fixtures alone cannot detect a transpose or left/right
multiplication error.

## Hierarchical condition schemas

The current LTA data do not occupy a full composition-temperature-strain
Cartesian product. The LTA profile therefore defines:

```text
unstrained family:
    composition x temperature x regime

strained family:
    composition x reference-condition x strain-mode x sign x regime
```

Only observed and scientifically applicable strata are required. Empty
combinations are not treated as missing data.

# Stress and virial contract

The MACE export specification is normative about stress.

Canonical `REF_stress` is:

- Cauchy stress in eV/Angstrom^3;
- a symmetric 3 x 3 tensor in Cartesian coordinates;
- ASE sign convention as verified against the chosen MACE release;
- no engineering factor applied to off-diagonal tensor components.

If six-component storage is used in an intermediate artifact, its order is
explicitly recorded and round-tripped through ASE. Virial labels are stored
under a different key and never silently relabeled as stress.

Every source domain must pass:

1. unit conversion test;
2. sign test against a finite strain energy derivative;
3. 3 x 3 to Voigt round trip;
4. shear-component test;
5. MACE read-back test.

Frames without valid stress may still train on energy and forces by using a
zero stress weight, but only under an explicit heterogeneous-label policy [8].

# Eligibility and quality screening

## Run-level state

```text
strictly_qualified
degraded_quality
unqualified
unresolved
```

The branch reuses the existing mdstats trajectory-quality evidence and records
all overrides.

## Labeled-frame eligibility

`FrameEligibilityDecision` applies after DFT labels exist.

Hard rejection includes:

- missing selected energy;
- missing or nonfinite forces;
- nonfinite positions or cell;
- singular cell;
- corrupt atom identity or ordering;
- truncated ionic step;
- catastrophic overlap;
- disallowed SCF nonconvergence.

Soft flags include:

- transient regime;
- high but physical force;
- unusual pressure or stress;
- rare coordination;
- cation transition;
- topology change;
- high foundation-model residual;
- degraded numerical quality.

A percentile tail alone is never a rejection reason.

## Candidate admissibility before DFT

An active-learning candidate has no DFT labels. It receives a separate
`CandidateAdmissibilityDecision` based on:

- finite cell and coordinates;
- minimum-distance safety;
- chemically allowed elements and counts;
- topology or framework sanity;
- integrator and trajectory integrity;
- model committee outputs;
- descriptor availability.

After DFT labeling, the candidate becomes a source occurrence and undergoes the
full labeled-frame eligibility audit.

# Material-profile and feature-provider architecture

DATA9A7a implements the declarative profile boundary:

```python
class SystemProfileProvider(Protocol):
    provider_id: str
    provider_version: str

    def build_profile(self) -> MaterialProfileIdentity: ...
    def build_atom_groups(self, profile) -> AtomGroupCatalog: ...
    def build_condition_axes(self, profile) -> ConditionAxisCatalog: ...
    def build_independence_axes(self, profile) -> IndependenceAxisCatalog: ...
```

This first protocol deliberately does not calculate scientific features. It
identifies the material, its phases, geometry, chemistry modifiers, optional
extensions, meaningful atom groups, condition axes, and independence axes.
The user explicitly declares the production profile; an automatic suggestion is
advisory until confirmed.

A material profile is compositional rather than a flat enum. One or more phase
components are combined with a geometry. For example, a solid-liquid interface
contains separate crystalline-solid and liquid phase components under the
`interface` geometry. Structural extensions such as `porous_network`, `zeolite`,
and `lta` are optional and hierarchical. The generic one-phase fallback defines
only `all_atoms`; a multi-phase profile must explicitly define phase membership.

DATA9A7b implements the first separate provider catalog for selection-grade
local structure and generic structural events. Later stages add phase-specific
activation, partition-critical profile features, additional selection evidence,
and metric-group policies. They do not silently enlarge `SystemProfileProvider`,
which remains the stable declarative identity contract.

The current DATA4-DATA7 implementation contains a generic universal path and
optional provider-specific extensions. DATA9A7d migrates the LTA implementation
behind the common extension envelope; LTA-named Python attributes remain only
as compatibility views for historical bundles.

A representative solid-liquid interface profile is expressed as:

```text
profile_id: lta-salt-interface
geometry: interface
phases:
  framework:
    phase_kind: crystalline_solid
    atom_groups: [framework_atoms]
    chemistry_modifiers: [ionic, covalent_network]
  molten_salt:
    phase_kind: liquid
    atom_groups: [salt_atoms]
    chemistry_modifiers: [ionic]
extensions: [porous_network, zeolite, lta]
```

This profile declares identity only. DATA9A7b provides a universal structural
provider that may be activated for any declared material profile; DATA9A7c and
DATA9A7d decide which phase-specific and optional-extension providers are added.
Analysis-owned validation calls remain separate.

A separate fold transformation implements:

```python
class FoldFeatureTransform(Protocol):
    def fit(self, training_frame_uids): ...
    def transform(self, frame_uids): ...
```

Raw scientific features and fitted statistical transforms are therefore not
confused.

## Universal structural selection features (DATA9A7b)

The universal structural provider is an interpretable complement to learned
MACE descriptors. For pair separation $r_{ij}$, it defines a continuous
chemistry-scaled weight from the sum of declared covalent radii. Smooth
coordination is the weighted degree, while the support-neighbor count records
how many pair weights exceed the numerical floor. Radial Gaussian projections
summarize neighbor-shell occupancy without locating RDF peaks or minima.
Weighted Legendre moments summarize neighbor-pair angles, and weighted spherical
harmonics produce rotationally invariant $q_4$ and $q_6$ order parameters.
A Gaussian local-density proxy and neighbor-species entropy provide packing and
chemical-mixing information.

These quantities are selection descriptors, not replacements for analysis-owned
RDF, integer coordination, angle-distribution, structure-factor, or topology
results. Missing angular moments are represented by a zero fill plus an explicit
mask. All minimum-image, switching, radial-width, and orientational-order
parameters are part of immutable policy evidence.

Frame descriptors aggregate atomic features by declared atom groups and by each
element present in the authorized DATA6 domain. The element schema is not
constructed from locked-test geometry. Generic temporal events identify large
changes in smooth coordination, support-neighbor count, local density,
orientational order, or same-atom minimum-image displacement. They are candidate
selection anchors only; physical interpretation remains profile-specific.

## Raw thermodynamic features

- total and per-atom energy;
- composition-relative energy;
- RMS, maximum, and quantile force statistics;
- per-species force statistics;
- pressure and stress invariants;
- temperature;
- volume and density;
- SCF iteration statistics.

## Raw cell and geometry features

- cell lengths and angles;
- strain invariants;
- pair-specific minimum distances;
- coordination histograms;
- bond-length moments;
- bond-angle moments;
- coordination anomalies.

## Partition-critical system-profile features

Partitioning must know the rare categorical states that it promises to cover.
DATA4 therefore exposes a lightweight, full-resolution system-profile layer
before the outer partition is locked.

A general profile may provide categorical phase, environment, defect, molecular,
region, or event states. For the optional LTA extension this layer provides, at
minimum:

```text
framework/mobile-species roles
coarse 4R/6R/8R site class when resolvable
on-center/off-center class
coordination-change flag
site-change flag
ring-crossing flag
framework-integrity flag
```

These features are designed for strata and event protection, not for final
high-dimensional selection. If a required partition-critical classification is
unresolved, the partition reports the missing coverage rather than claiming a
balanced split.

## Optional porous/zeolite/LTA extension

These features activate only when the declared material profile requests the
corresponding extension. They are not defaults for ordinary crystals, liquids,
amorphous systems, or interfaces.

- Si-O and Al-O coordination;
- tetrahedral distortion;
- framework topology state;
- Li-O, Na-O, and K-O coordination;
- nearest 4R, 6R, and 8R identity;
- ring-center displacement;
- signed ring-plane distance;
- off-center displacement;
- site assignment;
- entry, exit, transition, and ring-crossing events.

## Optional MACE features

An optional `mdstats[mace]` provider may compute:

- foundation checkpoint identity and SHA-256;
- MACE version and source snapshot;
- invariant atomic descriptors;
- species-separated descriptor summaries;
- declared atom-group and species environment descriptors;
- zero-shot energy, force, and stress residuals.

MACE exposes learned descriptors for atomic environments [2]. PyTorch and MACE
remain optional dependencies.

## Label-derived difficulty-feature blinding

Descriptors depend only on geometry and a frozen model and may be computed for
all domains. Foundation residuals require DFT labels and are therefore private to
an authorized training domain:

```text
TrainingDifficultyFeatureCatalog
    Residuals allowed for fold-training or final-training selection.

BlindedEvaluationPredictionCatalog
    Predictions stored without exposing residual-based selection features.
```

Outer monitor, calibration, held-out-fold, and locked-test residuals must not
enter selection reports or feature fitting. Locked-test labels and residuals
remain sealed until post-freeze evaluation. A policy violation is a hard leakage
failure, even when the split itself is unchanged.

## Fitted transforms and heterogeneous feature metric

Raw feature providers are partition-independent. Dataset-dependent operations
are represented by distinct objects:

```text
FeatureMetricPolicyTemplate
FoldFeatureTransform[k]
FoldFeatureMetricFit[k]
FinalFeatureTransform
FinalFeatureMetricFit
```

For fold $k$, fitting may inspect only the fold gradient-training domain. The
held-out fold, fold checkpoint monitor, outer monitor, calibration cohort, and
locked tests may be transformed using frozen parameters but cannot influence
the fit.

A `FeatureMetricPolicyTemplate` defines:

```text
raw feature blocks
per-feature robust scaling rule
per-block normalization
retained dimension or PCA rule
block weights
species weights
missing-block behavior
distance metric
dtype and numerical tolerance
```

A fitted metric records the medians, scales, projections, covariance factors,
and retained dimensions learned from its declared training domain.

A block-normalized distance can be

$$
d^2(i,j)=
\sum_b w_b
\frac{
\left\|\mathbf z_i^{(b)}-\mathbf z_j^{(b)}\right\|_2^2
}{d_b},
$$

where $b$ is a feature block, $d_b$ is its retained dimension, and $w_b$ is an
explicit physical weight. Species-specific atomic-environment distances are
reported separately from configuration-level distances. Dividing by retained
dimension prevents a high-dimensional MACE descriptor block from dominating
low-dimensional physical features solely through component count.

Fold-local and final transforms and metric fits are serialized separately from
the static template.

# Event detection before thinning

Rare events may be shorter than a preliminary stride. The controlling order is:

1. source and label integrity screening on all frames;
2. event and change-point detection on all eligible frames;
3. preservation of compact event windows;
4. temporal thinning of the ordinary non-event pool;
5. descriptor and physical-feature selection.

An event window may include one frame before, a representative event frame, and
one frame after. The exact stencil is policy-controlled. Dozens of adjacent
frames from one event are not retained unless required by a transition-path
analysis.

# Autocorrelation and complete-frame blocks

## Observable families

Fast observables:

- potential energy;
- force RMS;
- pressure;
- temperature.

Slow observables:

- mobile-ion coordination;
- site identity;
- ring-plane coordinate;
- framework topology state.

Fast autocorrelation controls the minimum ordinary block size. Slow variables
diagnose whether site-level independence is available at all.

## Candidate stride in frames

The candidate stride is dimensionally defined as

$$
s_{\mathrm{candidate}}
=
\max\left[
 s_{\min},
 \left\lceil
 \frac{c\tau_{\mathrm{fast}}}{\Delta t_{\mathrm{frame}}}
 \right\rceil
\right],
$$

and

$$
\Delta t_{\mathrm{candidate}}
=
s_{\mathrm{candidate}}\Delta t_{\mathrm{frame}},
\qquad 0<c\le1.
$$

The stride applies only to the non-event pool.

## Complete-frame blocks

A `TrainingDataBlock` contains whole configurations over a contiguous interval:

```text
block_id
run_id
frame_start
frame_stop
represented_time
regime
correlation diagnostics
configuration fingerprints
```

Atoms from one frame are never assigned to different partitions.

## Purge width

A purge interval separates statistical roles. The policy records whether the
purge is based on:

- a multiple of fast autocorrelation time;
- a minimum physical duration;
- event boundaries;
- restart-overlap detection.

If a slow state never decorrelates, the report states that blocked temporal
splitting does not provide state-level independence.

# Outer partition architecture

## Independence hierarchy

Use the strongest available evidence level:

1. independent replica or velocity seed;
2. independent cation ordering;
3. independent thermodynamic run;
4. purged temporal block within one run.

Temporal separation does not create an independent metastable state when the
slow variable never decorrelates.

## Partition-role feasibility

Before assigning roles, a `PartitionRoleBudgetPolicy` states the requested
cohorts and minimum support. A `PartitionFeasibilityReport` evaluates whether the
available independent blocks can support:

```text
development_pool
outer_monitor_validation
uncertainty_calibration
locked_interpolation_test
locked_challenge_tests
cross-validation folds
nested checkpoint monitors
purge intervals
```

Possible outcomes are:

```text
fully_supported
supported_with_temporal_blocks_only
calibration_deferred
challenge_set_external_only
reduced_cross_validation_folds
insufficient_for_locked_test
insufficient_for_requested_roles
```

The workflow never carves every desired role from a short trajectory merely to
satisfy a percentage. A calibration cohort or challenge set may be deferred to
later independent calculations.

## Outer domains

For each target `LabelDomain`, define:

```text
development_pool
outer_monitor_validation
uncertainty_calibration
locked_interpolation_test
zero or more locked_challenge_tests
```

### Development pool

Only this domain supplies cross-validation fold-training and final target
training candidates.

### Outer monitor validation

This fixed, representative domain controls final-run monitoring, stopping, and
checkpoint choice and never supplies gradients. It is not the locked test.

### Uncertainty calibration

This domain is reserved for predictions from the actual final independent-seed
committee. Out-of-fold predictions may diagnose ranking behavior, but they do
not automatically calibrate numerical final-committee thresholds.

### Locked interpolation test

This domain estimates unseen-frame performance within sampled conditions. It
cannot affect hyperparameters, selection, calibration, acquisition, stopping,
checkpoint choice, or protocol design.

### Locked challenge tests

Examples include:

- omitted temperature;
- omitted composition;
- omitted strain mode;
- independent structural or chemical realization;
- migration-coordinate calculations.

These remain separate named evidence cohorts.

## Machine-readable independence evidence

Every outer, fold-evaluation, checkpoint-monitor, calibration, and test cohort
receives one or more evidence grades:

```text
independent_replica
independent_structural_realization
independent_thermodynamic_run
purged_temporal_block
slow_state_not_decorrelated
insufficient_independence
```

The report records purge width, autocorrelation evidence, duplicate checks, and
known limitations. Metrics must carry these grades.

# Independent cross-validation job families

## Invalid design that is prohibited

The same continuously trained model must not train on fold $F_1$, later call
$F_1$ validation, and report the result as out-of-fold evidence. Once a frame
has contributed a gradient, it is no longer independent validation evidence for
that model.

The held-out evaluation fold must also not control early stopping or checkpoint
choice. Selecting the best checkpoint on the evaluation fold would bias the
reported fold error.

## Correct cross-validation

For $K$ evaluation folds, create $K$ independent jobs. For job $k$, partition
the non-evaluation development data into:

```text
fold_training_domain_k
fold_checkpoint_monitor_k
held_out_evaluation_fold_k
```

The default checkpoint monitor is a deterministic, purged nested split carved
from the non-evaluation data. A versioned policy may instead use a declared
fixed monitor cohort, but the held-out evaluation fold is never used for model
selection.

Train a fresh model:

$$
M_k = \operatorname{Train}
\left(
S_k\left[T_k(\mathcal D_{\mathrm{fold\ train},k})\right],
\mathcal D_{\mathrm{checkpoint},k}
\right),
$$

where:

- $T_k$ is fitted only on the fold-training domain;
- $S_k$ selects only from that domain;
- the fold-local atomic-reference fit uses only that domain;
- the checkpoint monitor controls stopping and checkpoint choice but no gradients;
- $M_k$ has an independent initialization, optimizer, and checkpoint lineage.

Only after checkpoint choice is frozen is $M_k$ evaluated on the held-out fold
$\mathcal F_k$. Combining these predictions gives a genuine out-of-fold
catalog.

## Cross-validation output

```text
CrossValidationJobFamily
  evaluation-fold definitions
  fold-training domains
  fold checkpoint-monitor domains
  fold-local transforms and FeatureMetricPolicy records
  fold-local training selections
  fold-local AtomicReferenceFitRecord objects
  one development MACE bundle per fold
  fresh-seed and initialization contract
  held-out out-of-fold prediction catalog
  aggregate metrics with independence grades
```

Every fold uses the same `SelectionBudgetPolicy`. Equal nominal target sizes are
used where feasible; mandatory-anchor differences and actual counts are
reported. Hyperparameter comparisons use the same budget policy and coverage
criteria, not an assumption that different folds contain identical selected
frames.

Cross-validation selects policies and estimates development-domain performance.
It is not implemented as a rotating epoch schedule.

# Training-set selection

Selection runs only inside the applicable fold-training or final-training
domain. A `SelectionBudgetPolicy` fixes requested sizes, mandatory-anchor
requirements, evidence-class quotas, and deterministic interleaving.

## Deterministic quota-interleaved master order

The selector first resolves mandatory coverage anchors. Remaining positions are
filled by a deterministic interleaving schedule across evidence classes:

```text
representative coverage
species-environment coverage
rare events
descriptor FPS
difficulty enrichment
```

The policy stores either explicit counts or fractions for every target size. A
representative default may reserve, after mandatory anchors:

```text
representative coverage     45%
species environments        20%
rare events                  15%
descriptor FPS               10%
difficulty enrichment        10%
```

These values are project policy, not universal constants. Deficits in one class
are redistributed by a declared deterministic rule. This prevents later
selectors from being starved when an earlier class consumes the size budget.

Near-duplicate pruning occurs during construction. The result is one ordered
sequence

$$
q_1,q_2,\ldots,q_N,
$$

and requested datasets are prefixes:

$$
\mathcal T_n = \{q_1,\ldots,q_n\}.
$$

A requested size below the mandatory-anchor count fails explicitly.

## Mandatory hierarchical quotas

The generic rule is that every observed, applicable combination of declared
condition axes and protected event classes receives an auditable minimum
coverage request. The axis catalog is profile-provided and may include
composition, temperature, pressure, strain, phase, defect state, surface
termination, interface registry, molecular conformer, or preparation history.

For the optional LTA profile:

```text
unstrained: composition x temperature x regime
strained: composition x reference-condition x strain-mode x sign x regime
```

Only applicable observed strata are required.

## Representative anchors

Representative anchors preserve dense equilibrium regions and expected
production frequencies. Diversity-only sampling is insufficient because it may
overweight feature-space boundaries.

## Configuration-level FPS

Use the fitted heterogeneous feature metric. Deterministic farthest-point
sampling selects

$$
i^*=\arg\max_i\min_{j\in S}d(\mathbf z_i,\mathbf z_j),
$$

with stable `frame_uid` tie-breaking. Pure FPS is not the complete selector.

## Atom-group-specific environment selection

Run separate environment selection for every declared focus atom group. Groups
may be defined by species, molecule, phase, spatial region, defect neighborhood,
interface side, or profile-generated tags. Selecting an atomic environment adds
its parent configuration. Abundant atom groups cannot determine the complete
selection. The historical LTA implementation uses Li, Na, and K groups; these
identities are not core defaults.

## Rare-event anchors

Include a compact temporal stencil around profile-declared events. General
defaults include coordination or neighbor changes, connectivity changes, large
nonaffine displacements, local-density changes, phase/order changes, strain
extrema, and high but physical restoring-force excursions. Site changes,
ring-plane crossings, pore-window events, adsorption/desorption, or interphase
transfer activate only when their profile providers are present.

## Difficulty enrichment

Within the training domain only, add a controlled quota of configurations with
large foundation-model residuals, stratified by condition and species. These
label-derived features remain blinded in evaluation domains.

## Coverage diagnostics

Report by feature block, condition, and species:

- candidate-to-training nearest distance;
- selected-to-selected nearest distance;
- 90th and 95th percentile covering radius;
- physical-feature quantiles;
- event/state counts;
- redundancy fraction;
- budget realized by evidence class.

These metrics recommend a coverage-complete size. Learning curves remain
necessary to establish model adequacy.

# Training objective, weighting, and exposure

## Membership, weighting, and exposure are different

Training-set membership says a frame may be used. Weighting says how strongly
its labels affect the loss. Exposure says when and how often it is presented.

`TrainingObjectivePolicy` binds:

```text
loss family
energy/force/stress global weights
head weights
normalization conventions
missing-label behavior
robust-loss settings
```

`ConfigurationWeightPolicy` binds condition-, regime-, event-, and
quality-dependent configuration weights. `PropertyWeightPolicy` binds
per-configuration energy, force, stress, or virial weights.

`ExposureAssignment` records:

```text
frame_uid
head_id
eligible epochs
actual gradient exposures
configuration weight
energy/force/stress weights
sampling probability
random-seed lineage
```

## Atom-group force imbalance

A configuration may contain many more force components from an abundant host
group than from a scientifically critical minority group. Selection diversity
does not remove this loss imbalance. The first adapter uses the standard MACE
configuration/property-weight interface and therefore does not claim a general
atomwise group-weighted loss. It must:

- report force metrics for all declared evaluation groups;
- impose profile-declared group, stress, and replay constraints during checkpoint
  selection;
- record any custom atomwise or auxiliary objective as a distinct protocol
  identity.

The historical LTA profile defines framework and Li/Na/K groups. Other systems
may define defects, adsorbates, interface atoms, reactive centers, rare elements,
or molecular subunits.

## Exposure backends

```text
NATIVE_MACE_FIXED
CUSTOM_EPOCH_RESAMPLE
MULTI_JOB_RESAMPLE
FINAL_REFIT
```

### `NATIVE_MACE_FIXED`

All selected target and replay frames are present in fixed files. MACE shuffles
the training loader reproducibly. This is the only backend supported by the
first adapter.

### `CUSTOM_EPOCH_RESAMPLE`

A custom MACE/PyTorch adapter rebuilds eligible data loaders at epoch boundaries.
This requires runtime integration and is not deliverable by files alone.

### `MULTI_JOB_RESAMPLE`

A deterministic sequence of restart jobs uses different fixed subsets. Its
optimizer/checkpoint lineage is explicit and it is not equivalent to one native
MACE run.

### `FINAL_REFIT`

After protocol and epoch rules are frozen, all declared development data may be
used. If outer validation is consumed, the final model loses that independent
monitor and may be judged only on locked external evidence.

## MACE exposure realization

`MaceExposureRealizationRecord` compares exported intent with the actual loader:

```text
real_pt_data_ratio_threshold
pre-MACE target/replay counts
post-MACE effective target/replay counts
implicit duplication factor
expected and observed batches
configuration, energy, force, and stress exposures
```

MACE 0.3.16 can duplicate fine-tuning-head data when the target/replay ratio is
below `real_pt_data_ratio_threshold` [18]. The first adapter disables this
behavior where the locked CLI permits it; otherwise the duplication is declared
in `TrainingProtocolIdentity` and audited as realized exposure. Silent exposure
changes are prohibited.

Cross-validation is a job family, not an epoch mode.

# Multi-head replay and training-protocol contract

## Concept

Multi-head replay fine-tuning trains a shared MACE backbone on target data and a
foundation replay dataset with separate output heads. The replay objective helps
limit catastrophic forgetting while the target head adapts [11, 12].

## `TrainingProtocolIdentity`

Every cross-validation family and final run is bound to one complete protocol:

```text
foundation checkpoint and head
naive or multi-head mode
replay source, selection, and monitor
training objective and property weights
target/replay head weights
exposure backend and realized-balancing policy
checkpoint metric
MaceCheckpointControlPolicy
replay-retention policy
optimizer, scheduler, epoch cap, and seed policy
MACE adapter lock
```

Cross-validation results apply only to this identity. Hyperparameters selected
under naive fine-tuning are not automatically valid for replay fine-tuning.

## Separate lineages

Target and replay data retain separate:

```text
source catalog
label domain
atomic-reference policy
selection plan
training weights
exposure accounting
validation or sentinel monitoring
```

## Replay source modes

```text
MP_SHORTCUT
EXTERNAL_TRUE_LABEL
EXTERNAL_PSEUDOLABEL
PRESELECTED
```

The mdstats core records a `ReplayPreparationPlan`; it does not download replay
data. The optional MACE adapter may execute or print the official MACE selection
command.

## Replay-retention monitor and constraint

A training-only replay file is insufficient. The bundle also contains a
disjoint `replay_monitor.xyz` or named `foundation_retention_suite`.

For true-label replay, it measures held-out DFT errors. For pseudo-label replay,
it measures drift from the original foundation model on unseen sentinel
configurations.

A `ReplayRetentionPolicy` defines:

```text
retention metric
foundation or pre-fine-tuning baseline
tolerated degradation delta
aggregation across energy/force/stress
failure or override behavior
```

## Checkpoint metric and constrained choice

A `CheckpointMetricPolicy` defines the target checkpoint objective and all
constraints. It must include:

```text
primary target scalar
energy/force/stress normalization
Li/Na/K species metrics
worst-condition metrics
rare-event metrics
replay-retention constraint
missing-label behavior
```

A typical rule is

$$
\min_c L_{\mathrm{target\ monitor}}(c)
$$

subject to

$$
L_{F,\mathrm{Li/Na/K}}(c) \le \boldsymbol\delta_F,
\qquad
\Delta L_{\mathrm{replay\ monitor}}(c) \le \delta_{\mathrm{replay}}.
$$

The exact metrics and thresholds are project policy and are serialized.

## MACE checkpoint-control policy

MACE 0.3.16 evaluates all validation heads but uses the **last** validation head
for learning-rate scheduling, patience, and native best-checkpoint decisions
[17]. Its multi-head assembly places `pt_head` before target heads in the
versioned source [18], but this ordering is an implementation detail that must
be tested rather than assumed.

The initial adapter supports:

```text
NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT
```

It must:

1. verify by source lock and smoke test that the target checkpoint monitor is the
   last validation head controlling native scheduling;
2. use a fixed epoch cap and configure patience so the run is not terminated by
   replay-head behavior;
3. enable retention of every evaluation checkpoint;
4. evaluate each candidate checkpoint externally on the target checkpoint
   monitor and replay monitor;
5. apply `CheckpointMetricPolicy` deterministically;
6. fail closed if the tested head-order or checkpoint behavior changes.

Later modes may provide full external scheduler control or a custom training
loop. A post-training audit alone is insufficient if native early stopping was
allowed to terminate on the wrong head.

## Exposure diagnostic

A coarse intended ratio is

$$
R_{\mathrm{exposure}}=
\frac{N_{\mathrm{replay}}w_{\mathrm{pt}}}
{N_{\mathrm{target}}w_{\mathrm{target}}}.
$$

The realized record additionally counts implicit duplication, batches, and
energy/force/stress exposures. Intended counts never substitute for observed
loader behavior.

# MACE adapter and output contract

## Version lock and compatibility matrix

The initial adapter targets `mace-torch==0.3.16`, the current PyPI release at
this architecture revision [9]. Every supported version records:

```text
mace version
package wheel/source SHA-256
Git commit or tag
mace_run_train --help
fine_tuning_select --help
key parser, loader, and train-loop source digests
validated head order
validated checkpoint-control behavior
validated replay-ratio behavior
```

Documentation URLs alone are not treated as a stable API contract.

## Minimal XYZ plus complete sidecar manifest

Extended XYZ contains only MACE-readable labels, weights, and compact stable
identities. Long provenance and reason lists live in a sidecar frame manifest
keyed by `frame_uid`. DATA8 writes Cartesian positions and per-atom floating
labels with 17 significant decimal digits rather than ASE 3.29's eight-decimal
default, then certifies the artifact through a streamed ASE read-back.

Minimum target-frame XYZ fields are:

```text
REF_energy
REF_forces
REF_stress
frame_uid
config_type
config_weight
config_energy_weight
config_forces_weight
config_stress_weight
```

The sidecar stores geometry/label fingerprints, source lineage, composition,
temperature, ensemble, strain, regime, selection reasons, policy digests, and
all audit evidence.

## Separated development, calibration, and evaluation artifacts

```text
mace_artifacts/
  development_bundle/
    target_train.xyz
    target_valid.xyz
    replay_train.xyz
    replay_monitor.xyz
    mace_config.yaml
    frame_manifest.json
    target_label_domain.json
    structural_atomic_reference_report.json
    atomic_reference_fit.json
    feature_metric_fit.json
    training_objective_policy.json
    checkpoint_metric_policy.json
    training_protocol_identity.json
    mace_checkpoint_control_policy.json
    replay_plan.json
    replay_retention_policy.json
    selection_manifest.json
    exposure_backend_policy.json
    adapter_lock.json
    cross_validation/
      fold_00/
        train.xyz
        checkpoint_monitor.xyz
        replay_train.xyz
        replay_monitor.xyz
        mace_config.yaml
        transform.json
        feature_metric_fit.json
        selection.json
        atomic_reference_fit.json
        training_protocol_identity.json
      fold_01/
        ...

  calibration_bundle/
    calibration.xyz
    committee_identity.json
    calibration_policy.json

  sealed_evaluation_bundle/
    target_test.xyz
    challenge_tests/
    evaluation_commands.yaml
    bundle_digest.json

  evaluation_activation/
    protocol_freeze_record.json
    selected_committee_identity.json
    activation_decision.json

  evaluation_results/
    evaluation_result_catalog.json
```

Replay files are omitted when replay is disabled. A sealed evaluation bundle may
be prepared early, but it is not opened or referenced by training. Activation
requires a `ProtocolFreezeRecord`, complete `TrainingProtocolIdentity`, selected
committee digests, and checkpoint-selection decision.

## Explicit E0 serialization

`AtomicReferenceFitRecord` is converted to the exact MACE input accepted by the
version lock, normally an explicit atomic-number mapping:

```yaml
E0s:
  3:  -1.234
  8:  -2.345
  11: -3.456
  13: -4.567
  14: -5.678
  19: -6.789
```

The fit-record path and digest belong in provenance. A conceptual fit-record placeholder is never emitted as the MACE `E0s` value.

## One target label domain per bundle

The development configuration contains one target head and an optional replay
head. It contains no locked test path. Its exact schema is generated by the
locked adapter and must preserve target-last validation control under the
accepted checkpoint policy.

## Export and loader round trip

The gate verifies:

1. ASE write/read equality;
2. atom order;
3. cell and PBC;
4. selected energy;
5. forces;
6. stress convention;
7. weights;
8. head labels and validation order;
9. explicit E0 mapping;
10. MACE parser recognition;
11. effective target/replay counts after loader assembly;
12. LAMMPS element mapping at later deployment.

# Protocol-matched cross-validation and final training workflow

The recommended initial workflow is:

1. Build one immutable outer partition, feasibility report, and independence
   report.
2. Define candidate `TrainingProtocolIdentity` objects, including naive/replay
   mode, replay preparation, objective, exposure backend, and checkpoint policy.
3. For each protocol, create $K$ independent jobs. Each has a fold-training
   domain, nested checkpoint monitor, held-out evaluation fold, and the same
   protocol-matched replay lineage.
4. Fit fold-local transforms, metric, selection, and atomic references using
   only each fold-training domain.
5. Train one fresh model per fold under the version-tested MACE checkpoint
   control. Freeze the externally audited checkpoint without inspecting the
   held-out evaluation fold.
6. Evaluate the frozen checkpoint on the held-out fold and collect out-of-fold
   predictions and independence grades.
7. Compare complete protocols using aggregate out-of-fold metrics and the fixed
   outer monitor. A naive protocol and a replay protocol are compared as
   different identities.
8. Freeze the selected data, objective, replay, exposure, stopping, checkpoint,
   and seed policies.
9. Fit final transforms, selection, and atomic references on the final target
   training domain.
10. Train independent final seeds under the same frozen protocol and record
    actual MACE exposure realization.
11. Apply constrained checkpoint selection and create the final committee.
12. Run that committee on the dedicated calibration cohort, record its
    applicability domain, and calibrate numerical uncertainty thresholds.
13. Create a `ProtocolFreezeRecord`; activate the sealed evaluation bundle and
    evaluate locked tests once.
14. Use the calibrated committee for active learning within its applicability
    domain; use rank-only acquisition outside it until recalibration.

If a final-refit mode consumes the outer monitor, its protocol must use a
predeclared epoch/checkpoint rule and only locked external tests remain
independent evidence.

# Active-learning architecture

## Immutable loop

```text
trained independent-seed committee
  -> exploratory ASE/LAMMPS trajectories
  -> candidate occurrence catalog
  -> candidate admissibility
  -> physical events + descriptors + disagreement
  -> calibrated acquisition and burst deduplication
  -> DFT query manifest
  -> labeled source ingestion
  -> labeled-frame eligibility
  -> append-only child dataset version
  -> retraining
```

## Acquisition evidence

A candidate may be selected using a Pareto or quota policy over:

- committee force disagreement;
- energy or stress disagreement;
- nearest-training descriptor distance;
- rare-event or physical-risk state;
- condition coverage gap;
- redundancy penalty.

A single weighted sum may be reported, but individual components remain
available.

## Calibration, committee binding, and applicability

Committee disagreement is a ranking signal, not an error guarantee [13, 14].
The architecture distinguishes:

```text
OutOfFoldUncertaintyDiagnostic
    Tests whether uncertainty ranks error during development.

FinalCommitteeCalibration
    Sets numerical thresholds using predictions from the actual final
    committee on a dedicated calibration cohort.
```

A calibration record is bound to:

```text
committee model digests
architecture and number of members
target-training lineage
replay lineage and retention policy
seed policy
MACE version and adapter lock
precision and inference settings
calibration-cohort identity
```

`CalibrationApplicabilityDomain` additionally records:

```text
elements and compositions
temperature and strain range
cell-size range
site and event classes
descriptor-distance range
force/stress range
framework-integrity state
```

A `CalibrationTransferDecision` classifies each candidate domain as:

```text
within_calibrated_domain
rank_only_outside_domain
recalibration_required
rejected_incompatible_domain
```

Out-of-fold predictions alone do not define the numerical scale for a committee
trained on full development data. If no valid final-committee calibration
cohort exists, the workflow emits only an explicitly **uncalibrated rank-only**
acquisition plan.

Report:

- Spearman uncertainty-error correlation;
- high-error recall in top uncertainty quantiles;
- false-negative rate;
- per-species and per-condition calibration;
- applicability-domain coverage;
- calibration transfer warnings when committee identity or candidate domain
  changes.

Locked tests are excluded.

## Burst deduplication

Adjacent uncertain frames from one event are clustered by trajectory, time,
geometry fingerprint, descriptor distance, and event identity. A compact
representative stencil is selected.

## Append-only role inheritance

A child dataset inherits all existing frame roles unchanged by default:

```text
existing development/validation/calibration/test roles
    -> inherited unchanged

selection-biased active-learning labels
    -> new development/training candidate pool

independent random labels from a newly entered domain
    -> possible new calibration or validation cohort

predeclared physical challenge calculations
    -> new named locked challenge set
```

A complete repartition is permitted only as a new evaluation lineage with a new
partition identity. Its metrics must not be presented as directly comparable to
the old locked-test lineage without qualification.

# Determinism and reproducibility

Every build records:

- source digests and source identities;
- parser and mdstats versions;
- policies and policy digests;
- reference-cell identities and cell-matrix convention;
- feature-provider versions;
- foundation checkpoint digest;
- MACE adapter lock and compatibility-test evidence;
- random seeds and floating-point dtype;
- `FeatureMetricPolicyTemplate` plus fold/final fitted metrics;
- fold checkpoint-monitor policy;
- fold and final `AtomicReferenceFitRecord` objects;
- `PartitionRoleBudgetPolicy`, feasibility, and independence reports;
- `SelectionBudgetPolicy` and realized evidence-class budgets;
- `TrainingObjectivePolicy`, configuration/property weights, and
  `CheckpointMetricPolicy`;
- complete `TrainingProtocolIdentity`;
- MACE checkpoint-control and exposure-backend policies;
- `MaceExposureRealizationRecord`;
- replay-retention and checkpoint-selection decisions;
- protocol-freeze and evaluation-activation records;
- calibration applicability and transfer decisions;
- active-learning role-inheritance policy;
- tie-breaking rules, fold assignments, selection master order, and output
  checksums.

# Performance and storage

The first implementation processes one trajectory at a time. It stores compact
metadata and feature arrays, releases full trajectories, and uses one of two
explicit export policies:

```text
SEQUENTIAL_REPARSE
    Reparse each source sequentially and emit selected frames.

SELECTED_FRAME_CACHE
    Cache selected atomic arrays during the first pass after the selection is
    known through a second controlled source pass.
```

The architecture does not promise XML random access. A later indexed or
streaming VASP reader may replace the second sequential parse without changing
scientific contracts.

# Failure semantics

The workflow fails closed when:

- source or label identity is unresolved;
- required labels are absent or nonfinite;
- incompatible label domains are mixed;
- strain requires an ambiguous reference cell or the cell convention is unclear;
- requested partition roles are statistically infeasible under the declared
  independence policy;
- locked or monitor labels reach a fitted transform, E0 fit, selector, difficulty
  feature, calibration, or acquisition operation;
- `E0s: estimated` is requested without an accepted training-domain
  atomic-reference fit or exact adapter serialization;
- a cross-validation held-out fold controls checkpoint selection;
- a cross-validation family is not bound to the same complete training protocol
  used for final training;
- the tested MACE validation-head order or native checkpoint behavior changes;
- native MACE silently changes target/replay exposure without an accepted
  realization record;
- a locked-test path appears in a development MACE configuration;
- no checkpoint satisfies mandatory target, focus-group, or replay-retention
  constraints;
- replay checkpoint and replay source are incompatible;
- dynamic epoch resampling is requested through a fixed-file-only adapter;
- calibrated candidate acquisition is attempted outside the calibration
  applicability domain without rank-only fallback or recalibration;
- active-learning child generation reassigns existing roles without a new
  evaluation lineage.

The workflow reports, rather than fabricates, absent profile-declared transition events,
independent replicas, strain-composition combinations, calibration cohorts, or
challenge sets.

# Gated implementation sequence

## MLFF-DATA0 - Architecture gate

Deliver the canonical manuals, specification, typed dependency graph,
architecture tests, and release records.

Gate:

- no rotating single-model cross-validation;
- no fitted transform before partition;
- no label-domain ambiguity;
- no test-to-fit, calibration, or acquisition dependency;
- no coupled frame/partition/selection record;
- all architecture-review findings incorporated into the canonical plan.

## MLFF-DATA1 - implemented in 0.20.29a0 - Shared sampling primitives

Implemented generic autocorrelation estimation, contiguous-run handling,
complete-frame blocks, purge intervals, deterministic assignment, and effective
sample diagnostics. Stage 11 public records, numerical values, and serialized
artifacts remain unchanged for the frozen parity fixtures.

## MLFF-DATA2 - implemented in 0.20.30a0 - Source, labels, and structural reference-energy audit

Implemented manifest/discovery, source identities, composition, controls,
ensemble references, optional quality/production references, decomposed label
identities, named energy-channel selection, complete-link label domains, and
structural atomic-reference identifiability. The implementation remains source
level: frame identities, eligibility, conditions, and strain begin in DATA3.

## MLFF-DATA2A automatic review-manifest inference gate - implemented in 0.20.60a0

The campaign review manifest now distinguishes observed XML metadata, filename
strain candidates, and promoted operational assertions. `prepare` performs one
bounded-memory tolerant XML scan to recover target temperature, MD controls,
thermostat/ensemble classification, ordered species, and initial/calculation cell
matrices. Tolerant recovery exists only to reduce manual review work. The DATA2
source gate itself now also accepts a demonstrably trailing interrupted XML stream
when controls, atom identities, and complete ionic records are unambiguous. It
retains complete records, conditionally recovers one unclosed final calculation,
and records interruption evidence. Mid-file corruption or missing critical records
remain hard failures.

For the LTA profile, a `_strained.hydro`, `_strained.ortho`, or
`_strained.shear` filename creates a candidate. Values such as `+5`, `-2`, or an
explicit percent sign are percentages; sub-unit values retain fractional meaning.
Temperature tokens are removed only for reference identity matching and then used
as a ranking hint among geometry-passing references.

The actual deformation is reconstructed as `F = H_s H_0^{-1}` and separated by
right polar decomposition. Hydrostatic candidates require the requested volume
ratio and isotropic stretch. Orthorhombic candidates require
`diag(1+d,1-d,1/(1-d^2))` in reconstructed LTA conventional axes. Shear
candidates require the exact symmetric right-polar stretch of the signed `xy`
engineering simple shear used by the six-strain generator. Only relationships
within the frozen matrix, volume, rotation, and fixed-cell tolerances are promoted
to `reference_group`, `reference_run_id`, and strain assertions. Failed or
ambiguous candidates retain complete residual evidence and warnings but cannot
influence DATA3 reference cells, DATA5 partitioning, or condition reporting.

Manual approval therefore reviews a populated evidence record rather than asking
the user to reproduce facts already contained in source controls and cells.


## MLFF-DATA2 interrupted VASP stream recovery hardening - implemented in 0.20.61a0

ENS0 and DATA2 parse `vasprun.xml` incrementally. A parser failure is recoverable
only when its diagnostic is interruption-like and located at EOF. Every closed
ionic calculation is retained. An unclosed final calculation is retained only if
positions, cell, forces, and energy are complete; otherwise only that ambiguous
tail is discarded. The source bundle records parse completeness and tail action.
Requested-step incompletion and interrupted XML are soft-quality warnings, while
frame, force, energy, and label-domain integrity remain fail-closed.

## MLFF-DATA3 - implemented in 0.20.31a0 - Frame facts, identities, eligibility, conditions, and strain

Implemented immutable frame facts, manifest-bound occurrence and geometry/label identities, restart duplicate detection, eligibility, temperature, reference cells, and the normative ASE-row cell/deformation convention with shear/rotation fixtures.

## MLFF-DATA4 - implemented in 0.20.32a0 - Raw features, partition-critical profiles, events, and role budget

Implemented partition-independent thermodynamic, force, stress, cell, strain, density, and selected pair-geometry features; lightweight full-resolution LTA ring/site states; coordination, site-change, ring-crossing, framework-integrity, and threshold event bursts; canonical JSON feature caching; and `PartitionRoleBudgetPolicy`. Event anchors are detected on every eligible frame before any ordinary thinning, and protected windows remain explicit evidence. No fitted transform, statistical role assignment, label-derived evaluation residual, or MACE artifact is introduced.

## MLFF-DATA5 - implemented in 0.20.33a0 - Feasibility, outer partition, independence, and fold roles

Implemented condition-bounded, autocorrelation-aware `PartitionUnitCatalog` construction; deterministic development, outer-monitor, uncertainty-calibration, locked-test, and purge assignments; explicit feasibility outcomes and calibration deferral; machine-readable independence evidence for replicas, structural realizations, thermodynamic runs, purged temporal blocks, and unresolved slow states; independent cross-validation folds with nested checkpoint monitors; role-specific blinding; and fail-closed identity, event-window, role, and purge-neighbor leakage audits. Held-out evaluation units never control early stopping or checkpoint choice. No fitted transform, training selection, MACE descriptor, or MACE artifact is introduced.

## MLFF-DATA6 - implemented in 0.20.34a0 and generalized through 0.20.53a0 - Universal/profile descriptors, checkpoint-bound model evidence, and blinded difficulty

Implemented analysis-owned universal local-geometry catalogs, optional profile-extension evidence, an optional lazy MACE calculator adapter, checkpoint-bound atomic descriptor sidecars, canonical final-development and cross-validation-training difficulty domains, species-resolved energy/force/stress residuals restricted to authorized training domains, blinded outer-monitor/calibration/fold predictions, and sealed unmaterialized locked-test records. DATA9A9a adds the exact DATA5-authorized descriptor/prediction frame plan, per-frame prediction sidecars, atomic restart checkpoints, corruption verification/recomputation, and DATA6 schema-v5 binding that reuses persisted predictions without repeated foundation inference. No fitted scaler, PCA, feature metric, E0 fit, loss weighting, training selection, DATA8 artifact, or MACE training execution is introduced.

## MLFF-DATA7 - implemented in 0.20.35a0 - Fitted metrics, objectives, checkpoint metrics, E0 fits, and selection

Implemented canonical final-development and cross-validation-training fit domains; static feature-block templates; robust/standard fold-local fitted metrics with dimension-normalized block weights and optional deterministic PCA; explicit fold/final atomic-reference mappings with rank, null-space, residual, and transfer audits; training objective, configuration/property weight, and checkpoint-metric policies; quota-interleaved deterministic master orders; strict nested training-size ladders; and coverage reports. No MACE training file, replay dataset, checkpoint result, or locked-test evaluation is introduced.

## MLFF-DATA8 - implemented in 0.20.36a0 - MACE artifacts, replay preparation, and protocol identity

Implemented verified minimal extended XYZ plus sidecar export, explicit atomic-number E0 mappings, a `mace-torch==0.3.16` source compatibility probe, local replay train/monitor artifacts, the fixed-file `NATIVE_MACE_FIXED` backend, `MaceCheckpointControlPolicy`, complete `TrainingProtocolIdentity`, loader count/head-order dry runs, independent final and cross-validation job directories, fold-evaluation exclusion, and sealed unmaterialized locked interpolation tests. DATA8 writes executable artifacts but does not run training or choose a checkpoint.

## MLFF-DATA9 - integration qualification and protocol execution

### MLFF-DATA9A - integration and production qualification

DATA9A is a mandatory hardening gate. Foundation fine-tuning uses elemental
corrections fitted to `E_DFT - E_foundation`, not a direct decomposition of the
target total energies. The final target E0 mapping adds these corrections to the
checkpoint E0 values and is bound to the checkpoint digest. The gate also stages
portable foundation/replay resources, verifies every numerical field through an
ASE extended-XYZ round trip, audits replay properties and provenance, supports
explicit training-ladder sizes, qualifies the installed MACE runtime, and runs
the full 27-trajectory preparation/resource benchmark.

The runtime qualification reads the exact `install_requires` contract from the
supplied MACE `setup.cfg`; it does not maintain a second hand-written dependency
list. `MaceDependencyManifest` binds every distribution, import name, version
specifier, and source-file digest. `create_mace_runtime_environment()` creates an
isolated environment from explicit local archives or a deterministic wheelhouse.
Offline mode passes `--no-index`, records all install commands and artifact
SHA-256 values, and never inserts dependency stubs. The environment becomes
eligible for CLI smoke tests only when every MACE-required import succeeds,
every declared version specifier is satisfied, and both `mace.cli.run_train`
and `mace.cli.eval_configs` import from the intended MACE version.
`MaceRuntimeEnvironmentRecord` also preserves the base interpreter, inherited
Python search paths, installed versions, and version mismatches. CLI probes are
serialized as `MaceCliSmokeRecord`. This implements the complete dependency declaration published by
MACE 0.3.16, including packages such as e3nn, torch-ema, matscipy,
python-hostlist, GitPython, and lmdb [19].

The supplied offline wheelhouse now satisfies the complete source-declared MACE
0.3.16 dependency graph, including e3nn 0.4.4 and opt-einsum-fx. ASE 3.29.0,
MACE 0.3.16, and the MPA-0 medium checkpoint pass installed qualification and
CLI probes under PyTorch 2.10.0+cpu.

DATA9A2 adds `MaceConfigRealizationRecord` and
`MaceJobExecutionSmokeRecord`. DATA8 emits `atomic_numbers`, `heads`, and nested
head `E0s` as scalar Python-literal strings, uses lowercase `universal`, and
realizes preselected target/replay exposure in extended-XYZ configuration
weights rather than unsupported `weight_pt`/`weight_ft` options. The genuine
MACE parser and loader dry run, one-epoch two-head training, checkpoint/head
inventory, target-head extraction, and finite evaluation round trip are now
executable gates.

### MLFF-DATA9B - protocol-matched execution and freeze

DATA9B executes the independent fold and final jobs, evaluates all saved
checkpoints, enforces target/focus-group/stress/replay constraints, constructs
learning curves, compares naive and replay protocols, trains multiple seeds,
constructs the committee, extracts the target head, and freezes the protocol.

DATA9B1, implemented in 0.20.56a0, freezes the exact mode/selection-size/seed
campaign matrix after a passed DATA9A gate. It binds each run to an exact DATA8
job and precision-aware `mdstats-mace-train` wrapper, inventories checkpoint
bytes by SHA-256, records external target/replay metrics, applies the frozen
`CheckpointMetricPolicy`, and chooses only among admissible checkpoints with a
deterministic tie-break. DATA9B1 deliberately does not launch long MACE jobs,
aggregate folds/seeds, construct a committee, or emit `ProtocolFreezeRecord`;
those responsibilities are implemented by DATA9B2 below.

## MLFF-DATA9B1 campaign and checkpoint control - implemented in 0.20.56a0

`TrainingCampaignPolicy` freezes the exact per-method variant matrix: selection
size, manual optimizer seed, method-specific fold count (including final-only
zero-fold variants), final-development coverage, checkpoint preservation, and the
precision-aware MACE wrapper. Fold membership is separately frozen by a
method-specific SHA-256 partition seed. `build_training_campaign_plan` accepts only a
passed full DATA9A qualification record and DATA8 bundles sharing the qualified
source/frame/DATA5 and MACE-compatibility lineages. Protocol-family identities
exclude fold-local data and scalar seed; protocol-variant identities add the
seed. Every required variant must contain one final job and the exact declared
fold set.

`inventory_mace_checkpoints` records every checkpoint file by contained relative
path, epoch, byte size, and SHA-256 and rejects duplicate epochs, paths, or
content. `CheckpointMetricRecord` binds external target and replay-monitor
metrics to the exact checkpoint and monitor artifacts.
`assess_checkpoint_admissibility` applies all predeclared energy, focus-force,
stress, worst-condition, and replay-retention limits without discretionary
overrides. `select_checkpoint` requires complete metric coverage and chooses the
minimum frozen primary metric only among admissible candidates, with replay
degradation, epoch, and SHA-256 as deterministic tie-breakers.

## MLFF-DATA9B2 execution, aggregation, committee, and freeze - implemented in 0.20.57a0

`TrainingExecutionPolicy`, `TrainingRunAttemptRecord`, and
`TrainingRunExecutionRecord` supervise one exact campaign run with bounded
retries, policy-authorized `--restart_latest`, immutable stdout/stderr and
environment evidence, per-attempt atomic persistence, process-group timeout
termination with a frozen grace period, and byte-level checkpoint revalidation.

`CheckpointEvaluationPolicy` and `CheckpointEvaluationRecord` automatically
evaluate exact checkpoint bytes on immutable target and replay monitors with
the critical-FP64 patch installed. They materialize target energy/force/stress,
focus-group, worst-condition, combined-loss, and replay-retention metrics and
feed the existing DATA9B1 admissibility and selection machinery.

`ProtocolVariantAggregate` and `ProtocolFamilyAggregate` preserve fold and seed
boundaries. `LearningCurveRecord` orders comparable selection sizes without
assuming monotonicity. `ProtocolComparisonRecord` compares complete naive and
replay families by frozen cross-validated evidence.

`CommitteeMemberRecord` and `CommitteeIdentity` bind final-development seeds to
selected checkpoint bytes and precision-aware target-head exports.
`ProtocolFreezeRecord` freezes only production qualification, selected protocol,
committee, and final checkpoint identities. `EvaluationActivationDecision`
activates sealed evaluation only when frame, DATA5, committee, and freeze
lineage match exactly.

The infrastructure is implemented and verified with bounded process tests and
the supplied real MACE multi-head smoke model. Long production campaign
execution remains blocked until the real production DATA9A realization and
replay corpus pass the full gate.

## MLFF-DATA9B3 unified campaign CLI and bounded deployment verification - implemented in 0.20.58a0

DATA9B3 exposes the implemented DATA2-DATA9B2 path through one deliberate
source-checkout tool:

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml <command>
```

The user-facing command set is `init`, `doctor`, `prepare`, `preflight`,
`train`, `evaluate`, `verify`, `status`, `advance`, and `guide`. The interface
uses one annotated TOML configuration, one reviewed manifest, one SQLite state
database, generated MACE data, run checkpoints/logs, exported committee models,
and consolidated result/benchmark files. Native DATA8 sidecars and content-
addressed generations remain internal reproducibility evidence rather than
independent user decisions.

`prepare` stops at the first discovered manifest until the exact digest is
approved. It then wraps DATA2-DATA5, the restartable checkpoint-bound DATA6
sweep, all requested DATA7/DATA8 mode-size-seed variants, and the full DATA9A
production gate. `train` executes only the frozen campaign through the
`mdstats-mace-train` critical-precision wrapper and resumes native DATA9B2
records. `evaluate` audits every checkpoint, aggregates folds and seeds,
compares naive/replay families, exports the target-head committee, and freezes
the selected protocol.

DATA9B3 production execution includes an adaptive single-GPU process scheduler.
Independent fold/final jobs remain scientifically separate and keep unique
output/checkpoint directories, so they may execute concurrently without sharing
mutable model state. Admission is bounded jointly by CPU affinity/cgroup quota,
available host RAM, aggregate device memory, and aggregate GPU utilization.
CUDA starts with exactly one job. The scheduler considers one additional job
only after every active MACE process has emitted fresh optimizer records and
remained in true epoch compute for a sustained stabilization window. Stable
per-job VRAM and utilization increments are projected to the next concurrency
level; both predicted totals must remain strictly below their configured
ceilings. Defaults are 90% VRAM and 90% GPU utilization. Calibration resets after
each promotion, preventing a newly launched process's initialization phase from
authorizing another launch. Stable post-add saturation lowers only the future
replacement target; it never kills an active checkpoint-producing run. Native
BLAS/OpenMP thread counts are divided among concurrent MACE parents and their
frozen DataLoader workers to prevent nested CPU oversubscription. Concurrency is
runtime evidence, not DATA8 scientific identity, so completed runs remain valid
when the scheduler policy changes.

`CheckpointEvaluationPolicy` now separates the candidate replay head from the
replay-baseline head. Legacy multi-head baselines continue to use `pt_head`; a
single-head foundation checkpoint may omit the head selector. This closes the
pseudo-label baseline path without inventing a foundation `pt_head`.

The CLI also promotes replay from a syntactic input to a production gate. A
multi-head campaign binds pseudo-labels to the exact foundation checkpoint byte
hash, requires train/monitor geometry separation, finite labels, target-element
coverage, and configured minimum corpus sizes. Small smoke replay may be allowed
only by an explicit exploratory override and cannot silently authorize a
production campaign.

`verify` performs bounded NVE deployment prechecks for every frozen committee
member, configured structure, and temperature. It records finite energy/force,
linear energy drift, minimum periodic pair distance, and maximum force. The
default hard drift limit is 0.026 eV/atom/ps. This gate is deliberately narrower
than DATA11 scientific acceptance: RDF, coordination, site occupancy, VDOS,
and diffusion remain analysis-owned and must still be validated before
scientific deployment. Its result is explicitly classified as
`bounded_predeployment`, never as scientific acceptance.

## MLFF-DATA9B3A cuEquivariance campaign backend - implemented in 0.20.59a0

DATA9B3A makes MACE acceleration an explicit scientific-protocol input rather
than an ambient environment detail. `MaceAccelerationPolicy` resolves either
`e3nn` or `cueq`, carries `enable_cueq`, `only_cueq`, and fail-closed availability
semantics, and is included in the optimizer and complete training-protocol
identity. The campaign configuration records the resolved backend in an
`[acceleration]` section. `init` may inspect the active environment once, but an
active campaign rejects `auto`; subsequent environment changes cannot silently
change the backend.

For a CuEq campaign, `doctor` imports the three CuEq package layers, verifies
CUDA and MACE flag support, loads the exact foundation checkpoint, and performs
one finite energy/force/stress call on a real replay or target geometry with
`enable_cueq=True`. The resulting `MaceAccelerationProbe` records package and
CUDA versions, finite-result evidence, and any failure. Its digest is bound to
the training-campaign policy.

The frozen backend is propagated to the DATA6 foundation sweep, DATA8 MACE YAML,
parser realization, one-epoch preflight, supervised training, target/replay
checkpoint evaluation, and bounded NVE verification. A CuEq preflight also
requires training-log evidence that MACE converted the model to CuEq. Production
uses `only_cueq=false`, so MACE converts checkpoints back to portable e3nn form
before saving. Traditional LAMMPS model conversion remains a separate deployment
backend and is not implicitly qualified by Python CuEq execution.

No CuEq failure triggers implicit e3nn fallback. The user must explicitly select
`backend = "e3nn"`, rerun `doctor`, and accept the resulting new protocol identity.

## MLFF-DATA10 - Active learning and calibration applicability

Implement candidate admissibility, uncertainty diagnostics, final-committee
calibration, applicability/transfer decisions, calibrated or rank-only
acquisition, novelty/events, burst deduplication, DFT query/ingestion,
append-only role inheritance, and immutable child generations.

## MLFF-DATA11 - End-to-end scientific acceptance

Run the full mdstats regression suite, synthetic ensemble/strain matrix, real
LTA preparation, partition-feasibility cases, naive and replay protocol-matched
cross-validation smoke jobs, checkpoint-control and exposure-realization tests,
final committee calibration, sealed-test activation, active-learning replay, and
performance acceptance.

# Physical-observable validation ownership boundary

Physical observable calculation is not owned by `mdstats.training_data`. RDF,
coordination, neighbor-angle statistics, connectivity, topology statistics,
MSD, VACF, spectra, VDOS, diffusion, displacement distributions, current
correlations, and ionic conductivity remain authoritative in their respective
`mdstats.analysis` modules and architecture manuals.

The MLFF branch owns only:

1. choosing an advisory observable-recommendation profile and an explicit recipe;
2. constructing an immutable recipe of analysis call IDs and parameters;
3. running the same recipe on matched reference and MLFF collections;
4. preserving verified collection and frame-selection identity, symmetric reference
   and candidate trajectory-generation identity, runtime/capability identity,
   warning records, and analysis-owned result identities;
5. binding every execution to an explicit statistical role and, where required,
   to a predeclared comparison policy, protocol freeze, and test-activation record;
6. applying comparison and acceptance policies only after those policies are
   frozen and independently identified.

It does not own the numerical algorithms, normalization, neighbor definitions,
plateau estimators, spectral transforms, or graph statistics.

The analysis-owned standardized facade is
`mdstats.analysis.observable_validation`. The MLFF-owned thin bridge is
`mdstats.training_data.observable_validation`. The latter delegates through
`run_mlff_observable_validation` and stores no duplicate scientific arrays or
algorithms.

The initial `ObservableRecommendationProfile` values are `generic_condensed`,
`crystalline_solid`, `amorphous_solid`, `liquid`, and `interface`. These are
advisory call sets, not automatic material classifiers. The user still supplies
species/groups, cutoffs, projections, trajectory windows, thermodynamic
conditions, and any interface coordinate. Ionic transport is an explicit
extension. Porous, zeolite, ring, cage, and site calls are optional extensions
and must never be activated merely because the reference application is LTA.

## Selection features versus validation observables

Compact structural descriptors used for partitioning or frame selection are
MLFF workflow inputs. Full physical observables used to judge a trained model
remain analysis products. An MLFF feature provider may call a lower-level
analysis primitive when that primitive has an explicit per-frame contract, but
it must record the owner API and cannot redefine the observable. Expensive
trajectory observables such as diffusion, VDOS, conductivity, or residence
statistics are validation jobs, not ordinary frame-selection features.

## Implemented call boundary in 0.20.44a0 and consistency closure in 0.20.45a0

The first standardized recipe registry covers the implemented general
structural and dynamical calls, including RDF, coordination, bond angles,
atomic connectivity/statistics, MSD, VACF, velocity spectra, VDOS, VACF
diffusion, diffusion plateau selection, van Hove, non-Gaussian dynamics,
self-intermediate scattering, charge current, current correlation, ionic
conductivity, and Nernst-Einstein comparison. Native result dataclasses remain
owned by the analysis modules.

The 0.20.45a0 closure validates recipe dependencies at construction, preflights
machine-readable collection requirements, records versioned capability/codec
identity, captures warnings, per-call durations, and runtime versions, and binds
candidate model and MD protocol identity to paired evidence. DATA9A6c in
0.20.46a0 strengthens this contract: supplied collection identities are
recomputed and verified; location hints do not alter scientific identity;
reference and candidate generation records must both bind the output collection;
each native result receives an analysis-owned canonical digest; statistical role
and locked-test activation are explicit; and comparison-policy identity is
upstream of realized evidence. Comparison metrics and scientific acceptance
thresholds remain a future MLFF policy layer; call execution alone is not a
pass/fail judgment. Static EOS, elasticity, finite-temperature response,
viscosity, phonons, surfaces, interfaces, defects, and migration barriers are
owned by `thermomechanical_energetic_validation_architecture.md`.


## Statistical role, policy ordering, and locked-test leakage

Physical-observable evidence is assigned one explicit role:
`training_diagnostic`, `checkpoint_monitor`, `outer_validation`, `calibration`,
`locked_test`, or `external_benchmark`. The role is not inferred from a filename
or caller context.

A comparison policy is a predeclared object. The allowed dependency order is:

```text
ObservableComparisonPolicy
    +
ObservableValidationActivationRecord
    +
Reference/Candidate Collection and Generation Identities
    -> ObservableValidationEvidence
    -> ObservableComparisonResult
    -> ObservableAcceptanceDecision
```

The reverse edge is forbidden. Realized RDFs, diffusion coefficients, phonons,
or other physical results must not be inspected to choose their own acceptance
thresholds. A locked-test activation record additionally requires the frozen
training protocol, partition assignment, and explicit evaluation activation.
Locked-test observable evidence cannot alter feature fitting, selection,
training protocol, checkpoint selection, calibration policy, or acquisition.
The dependency graph represents this role specialization explicitly as `LOCKED_TEST_OBSERVABLE_EVIDENCE`; ordinary checkpoint-monitor evidence is not globally forbidden from later policy-governed checkpoint assessment.

`ObservableValidationEvidence` stores analysis-owned result identities, not a
second scientific result schema. The authoritative analysis module remains
responsible for serializing or identifying its native result. The MLFF layer
references that identity when comparing reference and candidate outputs.

# Required module specifications

Before each runtime stage, write or revise specifications for:

```text
sampling/autocorrelation
sampling/blocks
sampling/assignment
training_data/sources
training_data/label_domains
training_data/reference_energies
training_data/feature_metric
training_data/identity
training_data/eligibility
training_data/conditions
training_data/strain
training_data/events
training_data/features/base
training_data/material_profiles
training_data/atom_groups
training_data/profile_features
training_data/profile_events
training_data/features/lta  # optional compatibility profile
training_data/observable_comparisons
training_data/features/mace
training_data/partition
training_data/cross_validation
training_data/checkpoint_selection
training_data/independence
training_data/selection
training_data/exposure
training_data/replay
training_data/replay_retention
training_data/active_learning
training_data/role_inheritance
training_data/export/extxyz
training_data/export/mace
training_data/workflow
```

# Decision summary

The branch follows ten scientific rules.

1. **Independent evidence remains independent.** Cross-validation uses fresh
   models, nested checkpoint monitors, and evaluation folds that never control
   checkpoint choice.
2. **The complete training protocol is the comparison unit.** Replay, objective,
   checkpoint, and exposure choices are part of cross-validation identity.
3. **Selection and E0 fitting are training-domain local.** Transforms, fitted
   metrics, selection, residual difficulty, and atomic-reference corrections do
   not inspect held-out evidence.
4. **Physical facts and workflow decisions are separate.** Occurrence,
   geometry, labels, policies, fitted products, and runtime realizations remain
   distinct.
5. **Data and deformation conventions are explicit.** Label domains, stress,
   energy channels, E0 limitations, and ASE cell-matrix conventions are audited.
6. **Declared focus physics receives explicit coverage.** Profile events,
   atom-group environment quotas, group-resolved metrics, and rare transitions
   cannot be hidden by abundant host statistics. LTA/mobile-ion semantics are an
   optional specialization.
7. **Weights and exposure are audited.** Selection, property loss, head balance,
   and actual MACE loader duplication are separate records.
8. **Locked tests are operationally sealed.** Activation requires frozen
   protocol and committee identities.
9. **Replay and uncertainty policies are enforced.** Candidate checkpoints obey
   target/group/replay constraints, and calibration is bound to the actual final
   committee and an applicability domain.
10. **Expansion is append-only by default.** Active-learning children inherit
    existing roles and add new cohorts without silently rewriting old evidence.

# References

[1] I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi,
"MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and
Accurate Force Fields," *Advances in Neural Information Processing Systems*
**35**, 11423-11436 (2022). DOI:
[10.48550/arXiv.2206.07697](https://doi.org/10.48550/arXiv.2206.07697).

[2] ACEsuit, "MACE descriptors," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/descriptors.html](https://mace-docs.readthedocs.io/en/latest/guide/descriptors.html)
(accessed 2026-07-27).

[3] H. Flyvbjerg and H. G. Petersen, "Error Estimates on Averages of
Correlated Data," *Journal of Chemical Physics* **91**, 461-466 (1989). DOI:
[10.1063/1.457480](https://doi.org/10.1063/1.457480).

[4] J. Racine, "Consistent Cross-Validatory Model-Selection for Dependent
Data: hv-Block Cross-Validation," *Journal of Econometrics* **99**, 39-61
(2000). DOI:
[10.1016/S0304-4076(00)00030-0](https://doi.org/10.1016/S0304-4076(00)00030-0).

[5] D. R. Roberts, V. Bahn, S. Ciuti, et al., "Cross-Validation Strategies for
Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,"
*Ecography* **40**, 913-929 (2017). DOI:
[10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881).

[6] J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, "How to Validate
Machine-Learned Interatomic Potentials," *Journal of Chemical Physics* **158**,
121501 (2023). DOI:
[10.1063/5.0139611](https://doi.org/10.1063/5.0139611).

[7] VASP Software GmbH, "Smearing technique," VASP Wiki. Available at:
[https://vasp.at/wiki/Smearing_technique](https://vasp.at/wiki/Smearing_technique)
(accessed 2026-07-27).

[8] ACEsuit, "Training," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/training.html](https://mace-docs.readthedocs.io/en/latest/guide/training.html)
(accessed 2026-07-27).

[9] ACEsuit, `mace-torch` 0.3.16, Python Package Index, released 2026-05-10.
Available at:
[https://pypi.org/project/mace-torch/0.3.16/](https://pypi.org/project/mace-torch/0.3.16/)
(accessed 2026-07-27).

[10] ACEsuit, `estimate_e0s_from_foundation`, MACE reference implementation,
version-locked by the adapter at implementation time. Current source available
at:
[https://github.com/ACEsuit/mace/blob/main/mace/data/utils.py](https://github.com/ACEsuit/mace/blob/main/mace/data/utils.py)
(accessed 2026-07-27).

[11] ACEsuit, "Multihead Replay Finetuning," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/multihead_finetuning.html](https://mace-docs.readthedocs.io/en/latest/guide/multihead_finetuning.html)
(accessed 2026-07-27).

[12] ACEsuit, "Multihead Training for MACE," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/multihead_training.html](https://mace-docs.readthedocs.io/en/latest/guide/multihead_training.html)
(accessed 2026-07-27).

[13] C. Schran, K. Brezina, and O. Marsalek, "Committee Neural Network
Potentials Control Generalization Errors and Enable Active Learning,"
*Journal of Chemical Physics* **153**, 104105 (2020). DOI:
[10.1063/5.0016004](https://doi.org/10.1063/5.0016004).

[14] A. R. Tan, S. Urata, S. Goldman, J. C. B. Dietschreit, and
R. Gomez-Bombarelli, "Single-Model Uncertainty Quantification in Neural
Network Potentials Does Not Consistently Outperform Model Ensembles,"
*npj Computational Materials* **9**, 225 (2023). DOI:
[10.1038/s41524-023-01180-8](https://doi.org/10.1038/s41524-023-01180-8).

[15] I. Batatia, P. Benner, Y. Chiang, et al., "A Foundation Model for
Atomistic Materials Chemistry," *Journal of Chemical Physics* **163**, 184110
(2025). DOI:
[10.1063/5.0297006](https://doi.org/10.1063/5.0297006).

[16] M. Kulichenko, B. Nebgen, N. Lubbers, J. S. Smith, et al., "Data
Generation for Machine Learning Interatomic Potentials and Beyond," *Chemical
Reviews* **124**, 13681-13714 (2024). DOI:
[10.1021/acs.chemrev.4c00572](https://doi.org/10.1021/acs.chemrev.4c00572).

[17] ACEsuit, `mace.tools.train`, MACE version 0.3.16 source, especially the
validation-head iteration and last-head checkpoint rule. Available at:
[https://github.com/ACEsuit/mace/blob/v0.3.16/mace/tools/train.py](https://github.com/ACEsuit/mace/blob/v0.3.16/mace/tools/train.py)
(accessed 2026-07-27).

[18] ACEsuit, `mace.cli.run_train`, MACE version 0.3.16 source, especially
multi-head assembly, replay-ratio duplication, head ordering, and loader
construction. Available at:
[https://github.com/ACEsuit/mace/blob/v0.3.16/mace/cli/run_train.py](https://github.com/ACEsuit/mace/blob/v0.3.16/mace/cli/run_train.py)
(accessed 2026-07-27).


[19] ACEsuit, `mace-torch` version 0.3.16 `setup.cfg`, complete runtime
`install_requires` contract. Available at:
[https://github.com/ACEsuit/mace/blob/v0.3.16/setup.cfg](https://github.com/ACEsuit/mace/blob/v0.3.16/setup.cfg)
(accessed 2026-07-28).

[20] e3nn developers, `e3nn` 0.4.4 package metadata and dependency contract,
Python Package Index. Available at:
[https://pypi.org/project/e3nn/0.4.4/](https://pypi.org/project/e3nn/0.4.4/)
(accessed 2026-07-28).

[21] R. Kern, "A Simple File Format for NumPy Arrays," NumPy Enhancement
Proposal 1, 2007. Available at:
[https://numpy.org/doc/1.13/neps/npy-format.html](https://numpy.org/doc/1.13/neps/npy-format.html)
(accessed 2026-08-15).

[22] NumPy developers, "numpy.load," NumPy reference documentation. Available
at:
[https://numpy.org/doc/stable/reference/generated/numpy.load.html](https://numpy.org/doc/stable/reference/generated/numpy.load.html)
(accessed 2026-08-15).

[23] National Institute of Standards and Technology, *Secure Hash Standard
(SHS)*, FIPS PUB 180-4, 2015. DOI:
[10.6028/NIST.FIPS.180-4](https://doi.org/10.6028/NIST.FIPS.180-4).

[24] R. J. Hyndman and Y. Fan, "Sample Quantiles in Statistical Packages,"
*The American Statistician* **50**(4), 361--365 (1996). DOI:
[10.1080/00031305.1996.10473566](https://doi.org/10.1080/00031305.1996.10473566).

[25] J. L. Bentley, "Multidimensional Binary Search Trees Used for Associative
Searching," *Communications of the ACM* **18**(9), 509--517 (1975). DOI:
[10.1145/361002.361007](https://doi.org/10.1145/361002.361007).

[26] SciPy developers, "scipy.spatial.cKDTree," SciPy reference documentation.
Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html)
(accessed 2026-08-15).

[27] T. F. Gonzalez, "Clustering to Minimize the Maximum Intercluster
Distance," *Theoretical Computer Science* **38**, 293--306 (1985). DOI:
[10.1016/0304-3975(85)90224-5](https://doi.org/10.1016/0304-3975(85)90224-5).

[28] SciPy developers, "scipy.spatial.cKDTree.query," SciPy reference
documentation. Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html)
(accessed 2026-08-15).

[29] SciPy developers, "scipy.stats.wasserstein_distance," SciPy reference
documentation. Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html)
(accessed 2026-08-15).

[30] K. Jamieson and A. Talwalkar, "Non-stochastic Best Arm Identification and
Hyperparameter Optimization," *Proceedings of AISTATS*, PMLR 51:240--248, 2016.
Available at: [https://proceedings.mlr.press/v51/jamieson16.html](https://proceedings.mlr.press/v51/jamieson16.html).

[31] L. Li, K. Jamieson, G. DeSalvo, A. Rostamizadeh, and A. Talwalkar,
"Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization,"
*Journal of Machine Learning Research* **18**(185), 1--52 (2018). Available at:
[https://www.jmlr.org/papers/v18/16-558.html](https://www.jmlr.org/papers/v18/16-558.html).

## MLFF-DATA9A3 production qualification (0.20.40a0)

The complete 27-trajectory, 37,632-frame bulk-LTA target corpus passes DATA3,
DATA4, and DATA5. Scientific conditions are inferred from VASP metadata and
ionic arrays, never from filenames. DATA5 uses indexed frame-to-strain lookup,
constructs 97 partition units across 25 conditions and three folds, and passes
its leakage audit. Feasibility is supported with temporal blocks only; four
units retain insufficient slow-state independence. DATA9A remains incomplete
until site coverage, checkpoint-bound production DATA6/DATA7 evidence, DATA8
jobs, and the exact replay corpus are bound. DATA9B remains gated.


## MLFF-DATA9A4 selectable MACE precision (0.20.41a0)

### Precision ownership

The training precision is owned by `MaceOptimizerPolicy.default_dtype` and is
therefore part of `TrainingProtocolIdentity`. The supported values are
`float32` and `float64`. Cross-validation and final jobs that differ only in
precision are distinct protocols and SHALL NOT share a protocol freeze record.

The foundation-checkpoint dtype does not constrain the output dtype. The first
production adapter explicitly supports the supplied uniformly float64 MPA-0
checkpoint as the initializer for either selected precision. MACE performs the
runtime conversion when `default_dtype=float32`; mdstats does not rewrite or
mutate the foundation checkpoint.

### Runtime evidence

`MaceModelPrecisionRecord` loads one saved model on CPU and inventories every
floating parameter and buffer by dtype and element count. It fails closed on a
load error, no floating state, mixed floating state, or mismatch with the
expected dtype. Non-floating parameters and buffers are counted separately.

`MacePrecisionTransitionRecord` binds the foundation checkpoint identity, DATA8
job, optimizer policy, requested dtype, trained artifact, and optional extracted
target-head artifact. A passing record requires the trained and extracted model
to be uniformly equal to the requested precision. The record also states
whether a real float64-to-float32 conversion occurred.

The real execution smoke resolves precision from the immutable protocol. A CLI
precision override may only repeat that value; it cannot silently alter the job.
The generated YAML parser probe must return the same value before loader or
training execution is accepted.

### Single-head extraction boundary

MACE 0.3.16 rejects target-head removal when the trained artifact already
contains exactly one `target_head`. In that case the complete trained artifact
is already the target-head model and is recorded directly. Multi-head replay
models still require genuine `mace_select_head` extraction.

### Verified acceptance evidence

The supplied float64 MPA-0 medium checkpoint has passed one-epoch CPU transfer
smokes for both requested precisions. Saved final and target-head artifacts were
uniformly float32 for the float32 protocol and uniformly float64 for the
float64 control. A separate real 300 K Na-LTA smoke using frames 0 and 1000 for
training and frame 1999 for validation produced finite energy, force, and stress
outputs from a uniformly float32 saved model.


### Planned staged-precision successor

The DATA9A4 contract above remains authoritative for one-stage FP32 or FP64 protocols.
The post-0.20.105 `PREC1`--`PREC3` roadmap generalizes it to explicit multi-stage
training schedules without weakening one-stage identity or deployment semantics. In
particular, `refine` is represented as a distinct staged training protocol rather than
retroactively reinterpreting an existing FP32 protocol as FP64.

## MLFF-DATA9A5a critical-FP64 execution (0.20.42a0)

The model-body dtype and the critical global-operation dtype are separate contracts.
`MaceOptimizerPolicy.default_dtype` owns training-body precision, while Python/ASE
inference selects its body dtype when constructing the calculator.
`MaceCriticalPrecisionPolicy` safety-locks energy and virial reductions, returned
observables, and persistent ASE MD state to FP64 and disables TF32.

For `ScaleShiftMACE` 0.3.16, node reference and learned interaction energies are
cast before graph-contiguous FP64 segment reduction. Inference forces are
differentiated from the same FP64 interaction-energy scalar; global virials and
stresses are reduced from edge derivatives in FP64. The full-FP64 patched path
reproduces upstream MACE energy, force, and stress to machine precision.

Optimization-time force training is a documented boundary: the selected model
dtype owns the complete second-derivative graph because upstream MACE/e3nn cannot
backpropagate an FP64 scalar seed through an FP32 force Jacobian. This does not
alter the FP64 validation/evaluation/MD contract. The critical-FP64 runtime implementation is limited to the Python/ASE MACE
0.3.16 path. mdstats does not audit or reproduce LAMMPS, ML-IAP, Kokkos,
LibTorch, or accelerator mixed-precision internals; those semantics belong to
the downstream consumer.
No LAMMPS-specific implementation stage is part of the mdstats MLFF branch.


## MLFF-DATA9A5b deployment-artifact closure (0.20.43a0)

`MaceDeploymentExportPolicy` and `MaceDeploymentArtifact` close the mdstats-side
deployment boundary. A complete or extracted MACE model is exported as a
uniformly FP32 or FP64 artifact with digest-recorded serialization, deterministic semantic state conversion, exact
state-conversion verification after reload, source/output byte digests,
semantic state digests, and an immutable canonical-JSON manifest. The default
policy requires a model-specific source-versus-reloaded inference probe.

The source training dtype, source observed dtype, requested deployment dtype,
conversion kind, optional DATA9A4 transition digest, and optional target head
are bound independently. Float32-to-float64 promotion is explicitly recorded
as storage/execution promotion and never as recovery of lost precision.

The artifact safety-locks `downstream_runtime_precision_claimed` to false.
LAMMPS is a possible downstream consumer of the chosen FP32 or FP64 serialized
model, but LAMMPS reductions, Kokkos behavior, integrator state, and accelerator
precision are outside the mdstats dependency graph and acceptance gate.
Production DATA6-DATA8 realization remains gated until the general profile migration and comparison-policy stages are complete.

## MLFF-DATA9A6 observable-call ownership bridge (0.20.44a0)

The analysis branch owns the standardized observable registry and immutable
recipes. The MLFF branch owns only paired invocation and future comparison
policy. No RDF, coordination, angle, topology, dynamics, spectral, diffusion,
or conductivity algorithm is duplicated in `training_data`.

## MLFF-DATA9A6b architecture and observable-evidence consistency closure (0.20.45a0)

The closure makes the documented boundary executable evidence rather than a
convention. Recipes reject self, unknown, and forward dependencies at
construction. Capability records expose machine-checkable collection
requirements, versioned parameter codecs, owner-signature identities, required
arguments, and result hints. Execution preflights the collection, records owner
capability digests, captures warnings, stores per-call durations, and stores runtime versions.

`ObservableCollectionIdentity` binds exact frame selection, geometry, dynamics,
labels, provenance, and source-content identity while treating filesystem paths
as non-identity location hints. The flat advisory enum is renamed
`ObservableRecommendationProfile`; the old `MaterialValidationProfile` name
remains a compatibility alias and is not the future compositional
material-profile system. Static thermomechanical and energetic observables are
assigned to the separate
`thermomechanical_energetic_validation_architecture.md`.

## MLFF-DATA9A6c observable evidence and leakage closure (0.20.46a0)

DATA9A6c makes production evidence fail closed:

- caller-supplied collection identities are verified against the arrays actually
  analyzed;
- object-dtype identity arrays are rejected;
- reference and candidate trajectories use one symmetric
  `TrajectoryGenerationIdentity`, with the older MLFF-specific record retained
  only as a compatibility wrapper;
- complete lineage requires both generation records and exact
  `output_collection_digest` binding;
- each native analysis result receives an `ObservableResultIdentity` owned by
  the analysis facade;
- a restorable `MLFFObservableValidationEvidenceRecord` verifies persisted
  invocation evidence without loading large scientific arrays;
- `ObservableEvidenceRole` and `ObservableValidationActivationRecord` enforce
  partition, comparison-policy, protocol-freeze, and locked-test activation
  ordering;
- runtime identity uses the executing package version and source hash rather
  than trusting only installed distribution metadata;
- capability identity includes owner implementation source, stable manual ID,
  source-document path, and versioned documentation URI.

## MLFF-DATA9A7 general profile migration

### DATA9A7a - material-profile and atom-group contracts (implemented in 0.20.47a0)

The public `material_profiles` module now implements compositional phase,
geometry, chemistry-modifier, structural-extension, atom-group, condition-axis,
and independence-axis identities. `MaterialProfileContracts` binds the four
catalog families under one digest. `Data4FeatureBundle` schema v2 carries the
aggregate optionally for legacy compatibility, and the cache persists it as an
independent immutable artifact. No profile calculation activates LTA unless its
extension and policy are explicitly supplied.

### DATA9A7b - universal structural selection providers (implemented in 0.20.48a0)

`mdstats.analysis.local_structure` owns invariant local-geometry kernels:
chemistry-scaled smooth connectivity, coordination, radial Gaussian projections,
a local-density proxy, angular Legendre moments, and weighted $q_4/q_6$
orientational order. The initial transparent dense kernel fails closed above a
declared pair-work budget and may later be replaced by the shared cell-list or
Verlet backend without changing its public result contract.

`mdstats.training_data.structural_selection` owns only MLFF orchestration. It
binds provider/policy identity, applies DATA9A7a atom groups, aggregates
per-atom results into finite frame vectors with explicit missing masks, records
generic geometry-only events, and materializes authorized DATA5 roles. DATA6
schema v2 carries these catalogs while retaining DATA6-v1 read compatibility.
The DATA7 metric accepts an optional `universal_structural` block; generic
species-environment selection performs per-element farthest-point coverage on
the universal atomic descriptors, with historical LTA descriptors retained only
as a fallback. Existing checkpoint-bound MACE descriptors remain the learned
representation and novelty path.

The universal provider does not interpret smooth edges as chemical bonds, infer
reactions, claim diffusion, or calculate validation observables. It derives
feature columns only from authorized roles and never inspects sealed frames to
discover species. Phase-specific defaults, Voronoi/free-volume measures,
crystalline templates, and optional porous semantics remain later work.

### DATA9A7c - phase and geometry profiles (implemented in 0.20.49a0)

The DATA9A7a declarations now produce an immutable
`PhaseGeometrySelectionPlan`. The plan is policy evidence, not material
inference. Each declared phase contributes enabled universal feature families,
generic structural-event types, a transparent analysis-owned local-structure
policy, and advisory physical-observable profile IDs. Geometry composes those
phase defaults and determines ordered atom-group coverage priorities.

Crystalline solids retain radial, coordination, connectivity, density, angular,
chemical-neighbor, and orientational-order features. Amorphous solids and
liquids use a broader radial and local-density window; orientational order is
retained as a continuous local-order or freezing detector rather than a lattice
assumption. Molecular/gas-like phases omit bond-orientational order by default
while retaining pair, radial, coordination, connectivity, chemical, density,
and angular features.

Surface, interface, confined, and cluster geometries prefer explicitly declared
region roles. Missing optional region groups produce immutable warning codes;
the runtime never infers a surface plane, interface slab, or confinement region
from coordinates. Interfaces require two or more declared phases and compose the
selection and observable-call recommendations of those phases plus the
interface geometry profile.

DATA6 schema v3 carries the plan and requires every phase-aware universal
catalog to bind its plan digest and material-contract digest. User overrides may
change numerical thresholds or enabled families, but the policy is rebound to
the active plan and a foreign plan digest fails closed. Generic environment
selection covers priority atom groups within species before the ordinary
per-species pass. This supplies phase/region coverage without introducing
material-specific selection algorithms.

The plan may recommend currently executable observable-call profiles, but it
owns no RDF, coordination-distribution, angle, dynamics, transport, or
thermomechanical calculation. Scientifically material parameters remain
explicit in analysis-owned recipes.

### DATA9A7d - optional porous, zeolite, and LTA extensions (implemented in 0.20.50a0)

DATA9A7d completes the migration of material-specific structural semantics out
of generic DATA4--DATA7 schemas. Optional partition-critical and
selection-grade evidence is now stored in immutable `ProfileFeatureCatalog`
envelopes. Each envelope binds an extension ID, workflow stage, provider and
configuration identity, frame-catalog lineage, optional parent DATA4 lineage,
provider-owned payload schema, and canonical digest. The generic core owns this
envelope and its adapter protocol; the provider continues to own the numerical
and scientific meaning of the payload.

Canonical DATA4 schema v3 stores `profile_partition_features`; canonical DATA6
schema v4 stores `profile_selection_features`. The old
`lta_partition_features` and `lta_selection_features` attributes remain only as
compatibility views reconstructed from an active `lta` extension. New evidence
does not serialize LTA-named top-level fields. DATA4-v1/v2 and DATA6-v1/v2/v3
remain readable without inventing an extension or material profile.

The LTA adapter preserves the existing ring, cage, window, site, cation-state,
and crossing calculations exactly, but generic feature fitting and selection
consume only three common interfaces: a namespaced frame feature vector,
provider-owned atomic-environment records, and stable environment-class labels.
An LTA catalog is legal only when the explicit
`porous_network -> zeolite -> lta` extension chain is active. The ordinary
crystal, amorphous, liquid, molecular, surface, confined, and interface paths do
not invoke LTA code.

The same stage removes chemistry-specific decision defaults. Species columns
are derived only from species present in the authorized fitting domain.
Profile-declared groups with `mlff_focus`, `training_focus`, or
`validation_focus` roles control optional group-aware difficulty, objective,
and checkpoint policies; otherwise every present species is treated uniformly.
The removed cation-named compatibility fields are not part of canonical runtime schemas. `structural_realization_id` is the generic independence label, and production qualification reports generic
profile-extension coverage instead of LTA-site coverage.

These changes are an ownership and evidence migration, not a new physical
analysis. Ring/site numerical responsibility remains in the framework/ring and
LTA provider architecture. Observable validation remains analysis-owned.


### DATA9A7e - cross-system qualification (implemented in 0.20.51a0)

DATA9A7e executes bounded DATA4--DATA7 workflows for a generic crystal, an
amorphous solid, a liquid, a multiphase interface, and an LTA extension. Each
case binds material-profile identity, DATA4--DATA7 lineage, the realized
phase/geometry plan, enabled universal feature/event families, optional
extension IDs, nonempty selection evidence, and canonical serialization.

Generic cases require clean-interpreter evidence proving that importing
`mdstats` and exercising generic MLFF APIs does not import
`mdstats.training_data.lta_profile` or
`mdstats.training_data.lta_selection`. Public LTA symbols are resolved lazily.
Generic canonical DATA4/DATA6/DATA7 payloads are recursively audited for legacy
LTA fields and active `lta` extension IDs. The LTA case must instead prove the
explicit `porous_network -> zeolite -> lta` chain and carry LTA partition and
selection results only inside generic `ProfileFeatureCatalog` envelopes.

`ImportIsolationEvidence`, `CrossSystemQualificationCaseRecord`, and
`CrossSystemQualificationSuiteRecord` are immutable, digest-verified runtime
contracts. The suite requires every declared case and derives its pass state
from the constituent case evidence. This is software-path qualification, not a
claim that the bounded fixtures or a fitted model are physically predictive.
Physical validation remains analysis-owned and comparison policy remains
DATA9A8.

## MLFF-DATA9A8 profile-aware observable comparison policies - implemented in 0.20.52a0

DATA9A8 implements immutable comparison-policy records:

- `ObservableComparisonThresholds`;
- `ObservableScoreUncertainty`;
- `ObservableComparisonRule`;
- `ObservableComparisonPolicy`;
- `ObservableRuleComparisonResult`;
- `ObservableComparisonResult`; and
- `ObservableAcceptanceDecision`.

Rules
bind one native result field to a declared metric, recipe call, material-profile
identity, atom-group/condition scope, and two-level quality/acceptance threshold.

Implemented lower-is-better metrics are absolute error, symmetric relative
error, normalized RMSE, normalized integrated absolute error, Jensen--Shannon
distance, peak displacement, and exact mismatch. Curve interpolation is opt-in
and requires complete reference-axis coverage. Missing fields, incompatible
axes, invalid probability mass, or no jointly finite values produce an explicit
`indeterminate` result rather than an invented score.

The optional uncertainty record consumes independently justified uncertainty on
the comparison score. It does not estimate uncertainty from one correlated
trajectory. Acceptance uses the worst required rule; a weighted mean score is
reporting-only and cannot hide a required failure. Condition and atom-group
scopes are aggregated explicitly.

The comparison-policy digest must match the digest already frozen in
`ObservableValidationActivationRecord`. The policy also binds the recipe,
recommendation profile, optional full material-profile-contract digest, allowed
statistical roles, capability compatibility, and result-type compatibility. The
separate comparison and decision records preserve the DATA9A6c dependency order
and locked-test leakage gates.

Because the branch remains pre-1.0, DATA9A8 also removes misleading deprecated
Python aliases: the flat `MaterialValidationProfile`, the asymmetric
`MLFFTrajectoryGenerationIdentity`, cation-named objective/checkpoint accessors,
`species_aware_force_objective`, `PartitionUnit.cation_ordering_id`,
`IndependenceGrade.INDEPENDENT_CATION_ORDERING`, and the old species/site
coverage alias. Canonical names now describe recommendation profiles, symmetric
trajectory generation, focus groups, structural realizations, and environment
classes. Historical DATA4/DATA6 cache readers remain temporarily because they
protect package-generated artifacts and require a separate cache-migration
decision.

## MLFF-DATA9A9a restartable production DATA6 model sweep - implemented in 0.20.53a0

DATA9A9a converts the expensive checkpoint-bound DATA6 model pass into a
restartable evidence-producing stage. `Data6ModelSweepPlan` binds the DATA3
frame catalog, DATA5 partition, DATA6 policy, foundation checkpoint, descriptor
policy, exact descriptor frames, exact prediction frames, and all sealed or
excluded frames. The requested union cannot contain locked-test, purge, or
excluded frames.

Each descriptor is written to `descriptors/<frame_uid>.npy`; each energy, force,
and optional stress prediction is written to
`predictions/<frame_uid>.npz`. Per-frame records bind file SHA-256, numerical
shape/dtype, frame identity, checkpoint identity, and canonical content digests.
Completed records are appended to a plan-bound JSON-lines recovery journal.
`checkpoint_interval` controls durable journal flushes; it no longer triggers a
full-history rewrite. `Data6ModelSweepCheckpoint` is compacted once when the
invocation returns or fails. Resume merges a compatible legacy compact
checkpoint with later journal events, repairs a truncated final journal line,
and verifies required-artifact completeness, file identity, shape, dtype,
finiteness, and content before reuse. Invalid frames are either recomputed under
explicit execution policy or rejected.

This changes DATA6 bookkeeping from repeated growing-history serialization to
amortized linear work. Role membership is precomputed as hash sets, every frame
adds one journal event, and the canonical checkpoint/manifests require one final
linear compaction pass. Progress reporting separates restored frames from work
performed in the current invocation and estimates remaining time from a
smoothed recent throughput rather than a restart-inflated cumulative rate.

A complete sweep yields a descriptor manifest and
`AtomicModelPredictionManifest`.

`PersistentAtomicModelPredictionCache` lazily verifies prediction sidecars while
DATA6 constructs training residual and
blinded-summary catalogs; therefore DATA6 does not execute the foundation model
a second time. DATA6 schema v5 binds the sweep plan and checkpoint digest.
Historical DATA6 v1-v4 bundles remain readable but receive no fabricated sweep
identity.

The supplied MPA-0 checkpoint was exercised on a real 1,400-frame, 168-atom
Na-LTA source. Two bounded invocations resumed the same 1,380-frame authorized
plan and produced verified `168 x 256` descriptors and `168 x 3` force arrays.
This is an execution-path smoke, not completion of the full production corpus.

This bounded execution remains historical smoke evidence rather than a complete
production realization. In the current 0.20.58a0 workflow, the unified DATA9B3
`prepare` command resumes the complete 2,734-frame production sweep, materializes
final and fold-local DATA7 bundles, binds the exact replay corpus, emits all
DATA8 jobs, and refuses to authorize DATA9B training until the DATA9A production
gate passes.


## MLFF-DATA9A9b restartable production DATA6-DATA8 materialization - implemented in 0.20.54a0

DATA9A9b introduces `ProductionMaterializationPlan` as the immutable bridge from
one complete checkpoint-bound DATA6 sweep to final and fold-local DATA7 bundles
and executable DATA8 jobs. The plan binds source, frame, DATA4, DATA5, DATA6,
model-sweep checkpoint, descriptor manifest, prediction manifest, every
canonical DATA7 domain, all fitting and selection policies, the foundation
checkpoint, MACE compatibility evidence, the exact replay train/monitor plan,
and the DATA8 optimizer/checkpoint/export policies.

`ProductionMaterializationCheckpoint` is rewritten after each completed DATA7
domain. Each completed-domain artifact binds the canonical domain, native DATA7
bundle digest, relative file location, and file SHA-256. Valid domains are
reused after interruption. A modified or foreign DATA7 record is removed or
rejected under explicit execution policy and invalidates downstream DATA8
evidence.

DATA8 is constructed only after all final and fold-local DATA7 domains verify.
The staged replay files may differ bytewise from their source because DATA8
realizes fixed-file configuration weights, but their configuration identities,
labels, provenance, species, counts, and replay policy must remain semantically
identical. The resulting `ProductionData8ArtifactRecord` binds the native DATA8
bundle and a complete relative-path/file-SHA tree manifest. Partial DATA8 output
is not promoted into a complete checkpoint.

`ProductionMaterializationRecord` is relocatable: its scientific identity is the
verified checkpoint and native bundle digests, not the absolute directory in
which those files happen to reside. It can reload every DATA7 bundle and the
DATA8 bundle and supplies their exact digests to production qualification.

This implementation qualifies restart, tamper recovery, replay binding, four
final/fold jobs, sealed-evaluation exclusion, and installed-wheel behavior on a
bounded complete workflow. It does not claim that the full 2,734-frame LTA
production sweep has run to completion in this environment. DATA9B remains
closed until a complete DATA9A9b record is generated for the actual production
corpus.

## MLFF-DATA9A9c production-gate integrity closure - implemented in 0.20.55a0

The final DATA9A gate is now controlled by `ProductionCorpusPlan`. The plan
freezes exact source and frame catalogs, normalization/reference manifests,
expected run identities and frame counts, cross-validation fold count, generic
extension requirements, and required production artifacts. A bounded smoke corpus
can no longer satisfy a foreign production plan merely by changing an expected
source-count argument.

Foundation-model readiness is derived from a complete DATA6 model-sweep plan,
checkpoint, descriptor manifest, and prediction manifest. Foundation-residual E0
readiness is derived from every required DATA7 `AtomicReferenceFitRecord` and the
exact foundation checkpoint. Presence of DATA6 or DATA7 objects alone is not
evidence.

Replay artifacts now carry separate geometry and numerical-label identities.
Configuration-weight rewriting may change file bytes, but staged replay must
preserve energy, force, stress, provenance, and geometry payloads exactly. Local
paths are serialized as location hints but excluded from foundation and replay
scientific identities.

DATA8 is constructed in hidden staging, verified, moved into a
content-addressed generation directory, and exposed through an atomic symlink
switch. Direct materialization-record loaders reverify file and tree evidence
before deserializing native DATA7/DATA8 bundles. Optional extension requirements
are generic provider declarations rather than LTA/site special cases.


## MLFF campaign execution-performance architecture - implemented in 0.20.62a0

The campaign control plane now treats source decoding, normalized frame arrays,
scientific catalogs, and orchestration state as separate storage layers. Each
VASP source is decoded once by an isolated bounded worker. The worker performs
control extraction, frame recovery, quality assessment, production-regime
assessment, and normalized-array emission before exiting. DATA3--DATA8 reuse
the checksum-bound frame cache rather than reopening the XML source.

DATA4 keeps one typed LTA scientific payload. Generic profile envelopes retain
only its scientific digest and an in-memory binding; they do not deep-copy the
mobile-state hierarchy. The DATA4 bundle identity is Merkle-style over component
digests. Campaign persistence writes raw-frame, LTA-frame, LTA-mobile-state, and
event records as independently checksummed JSONL shards. SQLite stores a small
content-addressed pointer. Restoration verifies the manifest and every shard,
then reconstructs typed catalogs without first building a giant nested mapping.

Hot lookups are immutable indices constructed with each catalog. Frame UID, run
ID, environment, descriptor, prediction, eligibility, and training-weight
accesses are constant-time. Per-frame species and pair indices are precomputed.
Force quantiles use one NumPy call, and mobile-ion/framework coordination uses
vectorized minimum-image displacement tensors. Canonical serialization sorts
each mapping once and caches immutable record digests.

The command-line layer reports DATA2 source starts/completions, retained frame
counts, quality status, worker logs, elapsed time, and ETA. DATA4 reports every
raw-feature, LTA-feature, and event-scan run. Persistence, DATA6 sweeps, DATA7/8
materialization, MACE subprocesses, checkpoint evaluation, and verification
emit heartbeat or item-level progress. Manifest approval is an approval-only
transaction unless the user explicitly requests continuation.

This architecture is optimized within the current immutable Python record
schema. The remaining DATA4 wall time and memory are dominated by constructing
roughly 0.9 million scientifically required LTA mobile-state objects. A further
large reduction would require a separate columnar/compiled scientific-record
schema rather than another low-risk campaign-control refactor.


## MLFF campaign resource and parallel-execution architecture - implemented in 0.20.63a0

### Resource snapshot and hard budgets

Every campaign command resolves one `SystemResourceSnapshot` from the effective
CPU affinity/cgroup quota, currently available RAM, selected CUDA device, and free
VRAM. The default execution budgets are 0.90 of available CPU and GPU/VRAM
resources and 0.80 of currently available RAM. A worker plan must include both per-worker peak memory and memory reserved for the
parent-side immutable result. Task count, CPU budget, RAM budget, and explicit
user caps are all hard upper bounds. Resource discovery affects execution only;
it does not alter scientific selection, partition, or model identities.

### Process isolation boundary

Source XML ingestion and object-heavy DATA3/DATA4 trajectory kernels use process
isolation, not Python threads. Each high-volume feature task runs in a fresh
interpreter with BLAS/OpenMP thread counts fixed to one. At most the resolved
number of task/result files and subprocesses exist simultaneously. On completion,
the worker exits and releases parser, NumPy, ASE, and native-library memory before
the next trajectory is launched. Automatic mode may select one worker on very
small CPU allocations where startup overhead dominates.

### Compact LTA transfer

LTA workers compute all per-frame and per-mobile-ion scientific fields but transfer
compact typed columns. The parent constructs the immutable records once. The LTA
catalog identity binds frame-record and mobile-state column digests rather than
requiring a JSON/SHA traversal of every nested record. Event detection consumes
the catalog's prebuilt frame-to-state index and must not regroup the full mobile
state sequence.

### GPU execution boundary

GPU use is limited to numerically dense MACE operations. DATA6 may create a native
MACE graph batch, select its initial size from the configured fraction of free
VRAM, and halve/retry after CUDA OOM without discarding completed frame artifacts.
Native descriptor batches are forward-only: the adapter enters `torch.no_grad()`
and explicitly disables every MACE derivative-bearing output. Native prediction
batches remain gradient-enabled because MACE obtains forces and stress through
energy derivatives. These two autograd boundaries may not be merged.
Training and preflight use the frozen e3nn/CuEq acceleration policy and receive a
resource-bounded DataLoader worker count. XML parsing, provenance objects, catalog
construction, and short 168-atom feature kernels remain CPU processes because
GPU transfer and object-conversion costs are not economically justified.

### Progress contract

Every long stage prints the resolved resource snapshot, selected worker/batch
counts, memory estimates, per-run completions, elapsed time, ETA when measurable,
and heartbeat/log-growth evidence for external MACE processes. A silent period may
not be the only indication that work continues.

## Adaptive evaluation and verification concurrency - implemented in 0.20.86a0

Checkpoint evaluation now forms one campaign-wide queue over every uncached
shortlisted checkpoint in the selected run scope. This permits the common
true-label refresh case—one retained checkpoint per completed run—to execute
across folds, seeds, and training modes instead of falling back to a serial
run loop. Selection and campaign-state commits remain parent-owned and occur
only after authenticated task results return.

Bounded NVE verification similarly queues all uncached model/structure/
temperature cases. Every task owns a private mutable ASE/MACE calculator.
Checkpoint evaluation tasks own their materialized calculator model, while
monitor parsing and cache-enabled foundation-model metrics are synchronized by
immutable identity to prevent duplicate first-use work.

One `AdaptiveInferenceConcurrency` controller governs each phase. CPU jobs are
bounded by 90% of the effective thread allocation and 80% of currently
available RAM. CPU telemetry is measured over the process affinity mask and
normalized when a cgroup or scheduler quota exposes less capacity than that
mask. CUDA starts with one job. After a stable fixed window, one additional job
is admitted only when projected aggregate VRAM and projected aggregate GPU
utilization both remain strictly below 90%. Admitted jobs use distinct PyTorch
CUDA streams and synchronize before committing results. Missing GPU telemetry
therefore fails closed to one CUDA job rather than guessing.

These controls are runtime-only. They do not enter checkpoint evaluation,
selection, model export, or NVE scientific identities. Existing 0.20.85a0
verification-case caches remain reusable when their model, structure,
integration, acceleration, and dependency identities still match.

## True-inference telemetry gate - implemented in 0.20.87a0

Evaluation and verification calibration is now explicitly tied to model compute
rather than worker lifetime. Every adaptive worker receives a context-local,
idempotent first-forward callback. Checkpoint evaluation invokes it immediately
before the first batched MACE prediction. NVE verification invokes it immediately
before the first force or energy request. Checkpoint conversion, monitor parsing,
model/calculator construction, CUDA-context creation, velocity setup, and all other
initialization therefore remain outside admission telemetry.

The controller requires every active worker at the current concurrency level to
have signaled. It then starts a trailing 60-second calibration window. The window
requires enough samples to cover the configured duration, not merely the old
minimum sample count. Any active-count change or not-yet-signaled replacement
clears the window. A newly admitted job therefore cannot inherit the low-utility
initialization phase or the previous level's steady-state measurements.

CUDA admission continues to use mean aggregate true-inference VRAM and GPU utility
with configured per-job lower bounds and safety margins. Both projected totals must
remain strictly below 90%. CPU scheduling uses the same gate; its stateful `/proc`
counter is reset when all workers first enter inference so the first interval cannot
span setup. The 90% CPU/GPU and 80% RAM ceilings are unchanged.

The generated TOML now uses
`parallel_inference_calibration_window_seconds = 60.0`. Legacy stabilization keys
remain readable. The exact 10-second value emitted by 0.20.86a0 is migrated to 60
seconds, while other legacy values remain explicit and canonical calibration-window
keys take precedence. Scheduling remains runtime-only, so prior scientific caches
remain compatible.

## Mixed-stage admission and stage progress - implemented in 0.20.88a0

Evaluation and verification no longer wait for the first model forward pass before
starting admission telemetry. In practical LTA campaigns, checkpoint hashing and
deserialization, deployable-model reconstruction, monitor loading, and model/device
construction can dominate wall time while batched inference is short. The worker
therefore signals at its first computation-heavy operation: checkpoint
authentication for evaluation, and MACE model loading for bounded NVE verification.
A direct evaluation call that bypasses checkpoint materialization signals before
artifact authentication. Lightweight queue/thread launch remains outside telemetry.

After every active worker at the current concurrency level has signaled, the
controller averages the complete mixed-stage workload over a trailing 20-second
window. Checkpoint reconstruction, monitor loading, CUDA transfer, candidate and
foundation predictions, NVE integration, and metric reduction all remain in that
same window; stage transitions do not reset it. Active-count changes, unsignaled
replacement workers, telemetry loss, or an empty active set still clear calibration.
CUDA promotion continues to require both projected aggregate VRAM and GPU utility
strictly below 90%; CPU/RAM bounds remain 90% and 80%, respectively.

Training retains its separate true-epoch scheduler with a 60-second window. The
exact prior generated 180-second training value migrates to 60 seconds. For
evaluation/verification, the exact generated shared 60-second value from 0.20.87a0
and legacy 10-second value from 0.20.86a0 migrate to 20 seconds, while explicit
phase-specific and other custom values remain authoritative.

Each task now emits stage transitions such as checkpoint authentication,
reconstruction, monitor loading, candidate/foundation evaluation, model loading,
NVE integration, and metric finalization. Periodic scheduler messages aggregate all
active stages, so a long pre-inference operation remains visibly progressing.
Scheduling and progress remain runtime-only and do not alter scientific cache
identities.


## Single-job CUDA calibration for evaluation and verification - implemented in 0.20.89a0

The 0.20.88a0 mixed-stage window remained vulnerable to heterogeneous duty cycles:
long CPU/IO-heavy phases and short GPU bursts could make a 20-second aggregate mean
look artificially close to zero. Evaluation and bounded NVE verification therefore
now use one campaign-wide CUDA calibration at concurrency one. The clock starts when
the first task is submitted and runs for 180 seconds by default. If a short task
finishes, the next task continues serially under the same calibration clock; the
calibration is not tied to one checkpoint or one verification case.

GPU utilization and incremental VRAM are measured relative to the pre-launch GPU
baseline and filtered independently. Values below 1% are excluded before averaging.
This removes idle/setup gaps without erasing resident-memory evidence. The retained
means become the fixed per-job estimate for the remaining queue. The scheduler then
selects the largest concurrency whose projected GPU utilization and VRAM both remain
strictly below 90%, additionally bounded by CPU, RAM, explicit job caps, and task
count. The old configured VRAM-per-job guess is no longer a hard pre-calibration cap;
it is only a fallback if no measured VRAM sample exceeds the activity floor.

No repeated promotion/recalibration cycle is performed after the baseline is frozen.
Live GPU telemetry remains as a hard safety override if the admitted aggregate level
actually reaches a configured ceiling. CPU evaluation/verification retains the
20-second workload controller, RAM remains capped at 80%, and training retains its
separate 60-second true-epoch calibration. Existing stage-transition progress output
remains active; calibration heartbeats additionally expose elapsed time and retained
GPU/VRAM sample counts.


## Upper-tail CUDA calibration for evaluation and verification - implemented in 0.20.90a0

The 0.20.89a0 three-minute single-job calibration removed the strongest idle-sample
bias, but the ordinary mean of all retained nonzero samples could still understate
short GPU/VRAM bursts in heterogeneous evaluation and bounded NVE verification. The
current scheduler therefore extends the campaign-wide concurrency-one CUDA
calibration to 300 seconds and replaces the ordinary retained-sample mean with an
upper-tail mean.

After independently discarding incremental GPU-utilization and incremental-VRAM
samples below the 1% activity floor, mdstats sorts each retained distribution and
averages the highest `ceil(0.10*N)` samples (at least one sample whenever `N > 0`).
GPU and VRAM are summarized independently because their peaks can occur in different
stages. These upper-decile means are the fixed per-job resource estimates used to
select the remaining queue concurrency below the 90% GPU-utilization/VRAM ceilings.
The configured VRAM estimate remains fallback-only when no measured memory sample
crosses the floor.

Calibration continues across successive serial jobs until 300 seconds elapse or the
queue completes. CPU evaluation/verification remains on the 20-second workload
controller, training remains on the 60-second true-epoch scheduler, and RAM remains
capped at 80%. Runtime scheduling changes do not alter scientific cache identities.


## Peak-trimmed fixed CUDA estimate - implemented in 0.20.91a0

The 0.20.90a0 upper-decile estimator intentionally emphasized burst load, but the
very largest telemetry points can be brief kernel or allocation peaks that are not
representative of sustainable per-job demand. Evaluation/verification therefore
retain the five-minute, concurrency-one calibration and the independent 1% activity
filters, but now use a peak-trimmed upper-band statistic. For each retained resource
distribution mdstats sorts samples descending, discards the highest 10%, and averages
the next-highest 10%. With sufficient samples this approximates the 80th--90th
percentile band. GPU utilization and incremental VRAM remain summarized independently.

The calibrated per-job GPU-utilization estimate is authoritative for the rest of the
queue. Live utilization telemetry is diagnostic only and no longer lowers concurrency
when an instantaneous sample crosses 90%; such spikes are expected in heterogeneous
MACE evaluation. Live VRAM remains a hard guard at the configured memory ceiling,
because memory saturation can cause OOM rather than merely high occupancy. CPU
evaluation/verification remains on the 20-second controller, training remains on the
60-second true-epoch controller, and RAM remains capped at 80%.


## 85th--95th percentile CUDA estimate - implemented in 0.20.92a0

Real-campaign evaluation showed that the 0.20.91a0 80th--90th percentile band can
still underestimate sustained per-job demand. The five-minute single-job calibration,
independent 1% activity filters, fixed post-calibration utilization estimate, and live
VRAM guard are retained. Only the default robust statistic changes: mdstats now
discards the highest 5% of each retained GPU-utilization/VRAM distribution and
averages the next-highest 10%, approximating the 85th--95th percentile band.

The exact shared 0.20.91a0 generated 0.10 peak-trim setting migrates to 0.05 so an
existing campaign adopts the new default without rewriting its TOML. Explicit
phase-specific values and other custom shared values remain authoritative. This is a
runtime scheduling change only and does not alter scientific cache identities.

# Post-first-campaign optimization roadmap - recorded after 0.20.96a0

## Architecture decision and sequencing rule

The first real production campaign showed that the remaining dominant campaign
cost is no longer primarily a bad scientific-selection algorithm.  Most of the
previously dangerous frame-count scaling in DATA6/DATA7 has already been removed.
The next optimization cycle therefore targets repeated model reconstruction,
repeated model prediction, graph preparation, heterogeneous evaluation scheduling,
and verification kernels.

These changes **must not be implemented as one monolithic optimization pass**.
They cross checkpoint serialization, provenance, cache identities, GPU execution,
verification, and orchestration state.  Combining them would make numerical or
lineage regressions difficult to isolate during an active campaign.  The stages
below are ordered by immediate wall-time impact and implementation risk.

The binding order is:

1. `OPT-EVAL1` - fast checkpoint reconstruction and selected-model export;
2. `OPT-EVAL2` - persistent prediction reuse and foundation-prediction reuse;
3. `OPT-EVAL3` - monitor-level graph/data preparation caches;
4. `OPT-EVAL4` - staged evaluation producer/consumer pipeline;
5. `OPT-VERIFY1` - verification calculator reuse and neighbor-search scaling;
6. `OPT-CTRL1` - control-plane and telemetry cleanup.

A later stage may depend on contracts established by an earlier stage, but an
implementation may not silently change scientific evaluation identities merely to
improve runtime.  Performance-only changes should remain execution-policy or
reconstructable-cache changes unless the numerical computation itself changes.

## OPT-EVAL1 - fast checkpoint reconstruction and immediate export - implemented in 0.20.97a0

### Implementation status

OPT-EVAL1 is implemented in 0.20.97a0.  The runtime now uses the completed
training ``.model`` as an authenticated architecture template, memory-maps modern
PyTorch checkpoint storage where supported, requires exact state keys/shapes/dtypes
before restoration, reproduces MACE CuEq/OEq training-backend conversion under the
process-wide FX lock, and restores only ``checkpoint["model"]`` in-process.  If the
completed training model already carries the selected checkpoint state (normally the
last saved epoch), it is reused directly without another whole-model serialization.
Multi-head target extraction now calls MACE's own ``remove_pt_head`` utility
in-process and keeps the qualified wrapper as fallback.  LoRA and any strict state or
backend mismatch fail closed to the legacy sandboxed restart-export path.

The checkpoint-model cache records the reconstruction method and materialization
time.  Parent-level publication reports separate model-materialization and target-head
export timings so a user can distinguish post-selection work from scientific
evaluation.  Existing v1 checkpoint-model cache receipts remain readable.

### Motivation

Current checkpoint evaluation can be faster than post-selection finalization.
When a selected epoch is available only as a restart `*.pt` checkpoint and the
reconstructable deployable-model cache is cold, the present fallback launches the
qualified `mdstats-mace-train` executable in a sandbox, reconstructs the training
configuration, restores the checkpoint through MACE restart machinery, serializes
an intermediate whole `.model`, reloads it, extracts the target head, and finally
writes the parent-level deployment model.  This can dominate the wall time after
checkpoint metrics are already complete.

### Planned reconstruction hierarchy

Selected-checkpoint publication should use the following ordered fast paths:

1. **Authenticated training-model reuse.**  If the completed run already emitted a
   whole `.model` whose model-state identity is demonstrably identical to the
   selected checkpoint, use that object directly for target-head extraction.
2. **Authenticated checkpoint-model cache reuse.**  Reuse an existing reconstructed
   deployable model when its checkpoint, DATA8 configuration, architecture, head,
   precision, and dependency identities match.
3. **Direct checkpoint state restoration.**  Load one qualified architecture
   template, read the selected checkpoint with a memory-efficient `torch.load`
   path where supported, restore `checkpoint["model"]` through `load_state_dict`,
   and pass the resulting in-memory module directly to MACE/ASE export logic.
4. **Legacy subprocess reconstruction fallback.**  Retain the current sandboxed
   MACE restart reconstruction only as a compatibility/fail-closed fallback while
   direct reconstruction is being qualified.

Ordinary rejected checkpoints should not require persistent whole-model
serialization merely to compute metrics.  Only selected or explicitly requested
models need durable `.model` publication.

### Correctness gate

Direct reconstruction may become the default only after numerical equivalence is
verified against the legacy qualified reconstruction for representative final and
intermediate checkpoints.  At minimum the gate must compare:

- model/head identity and parameter/buffer dtype;
- energy predictions;
- force predictions;
- stress predictions where supported;
- target-head extraction and deployable-model reload;
- checkpoint/source SHA-256 immutability before and after reconstruction.

Differences must satisfy the declared numerical tolerance for the selected
precision policy.  A mismatch fails closed to the legacy reconstruction path.

### Progress and timing evidence

This stage should also add low-cost timing evidence around checkpoint load,
architecture/template load, state restoration, accelerator conversion, target-head
extraction, serialization, hashing, and atomic publication.  User-visible progress
must distinguish model finalization from scientific evaluation, for example:

```text
[MODEL EXPORT] <run>: checking existing training model
[MODEL EXPORT] <run>: restoring selected checkpoint weights
[MODEL EXPORT] <run>: extracting target head
[MODEL EXPORT] <run>: writing parent-level model atomically
[MODEL EXPORT] <run>: complete
```

The timing instrumentation is part of `OPT-EVAL1`; it is not a reason to defer the
checkpoint reconstruction fix to a separate preliminary optimization stage.

### OPT-EVAL1 qualification evidence

Focused qualification includes exact energy, force, and stress equality for an actual
MACE 0.3.16 e3nn model restored from a checkpoint state, exact target-head reload for
a real multi-head ``ScaleShiftMACE`` fixture, checkpoint SHA immutability, direct
final-epoch training-model reuse, dtype-mismatch fail-closed fallback, and guarded
CuEq round-trip coverage.  The remaining subprocess route is therefore a compatibility
fallback rather than the normal reconstruction path.

## OPT-EVAL2 - persistent prediction artifacts and foundation reuse - implemented in 0.20.98a0

### Implementation status

OPT-EVAL2 is implemented in 0.20.98a0. Evaluation prediction and metric identities are
now separate. Candidate target/replay energies, forces, and optional stresses are
persisted beneath the campaign-internal `evaluation-predictions/` store using a
content-addressed key that binds model SHA, head, ordered geometry identity, dtype,
device, acceleration policy, and a versioned numerical contract. Prediction payloads
are atomically published and SHA-256 authenticated; corrupt entries are misses.

Metric reduction consumes the current labelled monitor plus these immutable
predictions. Consequently a true-label replay correction or a metric-weight change can
rebuild evaluation records without repeating MACE inference. A complete candidate
prediction set is sufficient to rebuild metrics after the corresponding raw checkpoint
has been cleaned; a changed checkpoint file is never hidden by the cache and fails
closed.

Foundation predictions are also work-conserving. Matching DATA6 prediction artifacts
are reused for the target foundation comparison when checkpoint, default-head, dtype,
device, acceleration, frame order, and sidecar provenance match. Frozen
foundation-pseudolabel replay values may serve as the historical foundation predictions
for a geometry-identical TRUE_DFT replay monitor when the exact foundation checkpoint
and replay artifact are authenticated. Parallel checkpoint workers serialize only the
shared foundation miss-resolution path, so one worker imports/infers and followers
become cache hits while candidate inference remains parallel.

`CheckpointEvaluationRecord` schema v3 records optional prediction-artifact digests;
v1/v2 rows remain readable. Evaluation notes expose target/replay candidate/foundation
cache hit/miss state and prediction source. The outer TRUE_DFT evaluation-replay digest
versus nested DATA8 training-replay lineage split introduced earlier is unchanged.

### Correctness and restart gate

The implementation is qualified against the following cases:

- changing combined metric weights reuses the same candidate predictions;
- correcting TRUE_DFT replay labels with unchanged geometry reuses candidate target
  and replay predictions, including after raw-checkpoint cleanup;
- corrupted prediction bytes are rejected and recomputed when source bytes exist;
- missing checkpoint plus missing/corrupt prediction fails closed;
- DATA6 target-foundation predictions avoid repeated foundation inference;
- frozen replay pseudolabels avoid repeated foundation inference for matching
  TRUE_DFT replay geometry;
- concurrent checkpoint workers perform one shared foundation import/inference;
- legacy v1/v2 evaluation records migrate without scientific reinterpretation.

The frozen pseudolabel source represents the exact historical foundation outputs used
to construct replay regularization. It is authenticated by source bytes, geometry/order,
and foundation checkpoint identity; it is not presented as a claim that an arbitrary
new accelerator/runtime would reproduce those floating-point values bit-for-bit.

Detailed runtime/cache requirements are specified in the OPT-EVAL2 training-data
specification under `docs/specs/training_data/`.

## OPT-EVAL3 - monitor-level graph and immutable evaluation-view caching - implemented in 0.20.99a0

OPT-EVAL3 is implemented in 0.20.99a0. Evaluation no longer treats MACE graph
construction as an ephemeral per-calculator/per-batch side effect when the monitor
geometry is already frozen. Candidate/foundation checkpoint workers provide ordered
monitor geometry identities to the qualified native MACE batching path. A stable graph
key binds those identities to cutoff, species table, active head, calculator key maps,
dtype, graph-policy version, and the relevant MACE/PyTorch/ASE/e3nn/matscipy/NumPy/
torch-geometric dependency identity while deliberately excluding model weights. Epochs
and folds with the same graph policy can therefore share the same prepared geometry.

Two graph-cache tiers are used:

- a byte-bounded CPU memory cache (`MDSTATS_MACE_MONITOR_GRAPH_CACHE_BYTES`, default
  1 GiB), which keeps complete small-monitor shard sets resident when they fit; and
- SHA-256-authenticated persistent CPU graph shards under campaign-internal
  `evaluation-graphs/`, which avoid repeated `AtomicData.from_config` construction
  after eviction/restart for larger scans.

Corrupt, malformed, dependency-mismatched, or geometry-mismatched shards are cache
misses and are rebuilt from the authenticated source monitor. Parallel workers
single-flight the same stable shard miss. The graph cache remains reconstructable
execution evidence and never replaces source monitor SHA/lineage validation.

Graph ownership is also cheaper. Graphs are constructed on CPU and cached before one
host-to-device transfer, rather than building/moving a device batch and cloning it back
to CPU merely to populate the cache. Single-model MACE inference uses the freshly
materialized device batch directly; ensemble calculators retain per-model clone
isolation. Pinned-memory/nonblocking transfers remain intentionally disabled until
measurements justify them.

Repeated metric reduction now consumes a cached immutable evaluation view instead of
walking `Atoms.info`, `Atoms.arrays`, and atomic-number masks for every checkpoint. The
view precomputes configuration/atom counts, force offsets, reference energies/forces,
atomic numbers, focus-species local indices, condition IDs/labels, reference stresses,
and stress-valid masks. The byte budget is controlled by
`MDSTATS_MLFF_EVALUATION_VIEW_CACHE_BYTES` (default 512 MiB). Metric definitions and
combined-loss weights are unchanged.

The existing object-identity graph LRU remains available to DATA6 and other callers
without stable monitor identities. Evaluation batch sizing and recursive OOM backoff are
unchanged; geometry identities are split with the same batch so backoff shards remain
correctly bound. Single-frame remainder batches use the stable graph path as well.

Representative release-host timing isolated graph preparation on a real MACE 0.3.16
CPU fixture with 64 H2O frames: first graph construction was about 0.054 s and an
authenticated persistent-shard reload after memory-cache clear was about 0.0081 s
(~6.7x faster for graph preparation). A synthetic 2000-frame/96-atom monitor required
about 0.067 s to extract its immutable evaluation view, while a repeated in-memory view
lookup was about 15 microseconds. These are preparation measurements, not claims about
end-to-end GPU inference speedup.

Detailed identity, corruption, ownership, and compatibility requirements are specified
in the OPT-EVAL3 training-data specification under `docs/specs/training_data/`.

## OPT-EVAL4 - staged evaluation pipeline

`OPT-EVAL4` is implemented in mdstats 0.20.101a0. Evaluation no longer treats one
checkpoint as one heterogeneous worker occupying an accelerator-admission slot from
checkpoint I/O through metric persistence. The runtime is split into bounded stages:

```text
CPU monitor/cache preparation
        -> bounded prepared queue
accelerator-admitted checkpoint materialization + serialized CuEq/OEq/FX conversion
        -> private-worker MACE inference
        -> bounded finalization queue
CPU prediction persistence + metric reduction
        -> parent-thread durable commit / run selection / selected-model publication
```

The public `evaluate_mace_checkpoint()` surface remains synchronous and executes the
same stages sequentially. Campaign evaluation uses the staged surfaces directly so CPU
preparation for later checkpoints and CPU finalization for completed checkpoints can
overlap accelerator work. Cache-only OPT-EVAL2 recomputation bypasses accelerator
admission entirely.

A calculator/provider remains private to one inference worker. Candidate checkpoint
materialization occurs inside the admitted accelerator stage because CuEq/OEq direct
restoration and the qualified legacy fallback can execute device-bound conversion. MACE
FX conversion remains serialized by the process-wide conversion guard, while admitted
model forwards can overlap on separate CUDA streams.

The existing fixed post-calibration CUDA resource estimate remains authoritative.
Evaluation calibration now describes the accelerator stage rather than CPU monitor
parsing: model materialization, accelerator conversion, transfer, and inference are
included; CPU preparation and metric/persistence finalization are excluded. The hard
live VRAM safeguard remains.

CPU stage concurrency and backpressure are controlled by three bounded settings:

- `parallel_evaluation_prepare_jobs`;
- `parallel_evaluation_finalize_jobs`;
- `evaluation_pipeline_buffer_jobs`.

Zero selects conservative automatic values. A full finalization backlog applies
backpressure to inference so fresh prediction arrays cannot accumulate without bound.
Completed accelerator slots are refilled before parent-side selection/model-publication
callbacks run.

Per-checkpoint progress reports total wall time plus prepare/inference/finalization stage
time. These timings are diagnostic only and do not change prediction, graph, metric, or
selection identities. Existing 0.20.99/0.20.100 campaign state therefore remains
compatible. Detailed ownership, backpressure, restart, and acceptance requirements are
recorded in `docs/history/mlff/retired_specs/mlff_opt_eval4_staged_evaluation_pipeline_spec.md`.

## OPT-VERIFY1 - verification reuse and nearest-pair scaling

`OPT-VERIFY1` is implemented in mdstats 0.20.102a0. Bounded verification now parses
each authenticated structure file at most once into a calculator-free ASE template;
independent NVE cases copy that template before velocity initialization and dynamics.
If every case is already present in the durable verification cache, structures are
not parsed at all.

Each adaptive verification worker retains at most one private MACE calculator keyed
by model path, device, dtype, and acceleration-policy digest. Adjacent cases on the
same worker/model therefore reuse model deserialization and accelerator transfer. A
worker that moves to another model replaces its cached calculator, bounding resident
model state by scheduler concurrency. Mutable calculators are never shared between
threads.

The minimum-distance safety monitor no longer calls the full periodic `N x N`
distance matrix. It uses an adaptive periodic neighbor-list search beginning at a
local 2 angstrom radius and expands only when no distinct pair is found. The first
nonempty search yields the exact global nearest pair because every omitted pair lies
at or beyond the active radius. A wrapped-position bounding-box diagonal provides a
guaranteed terminal radius without allocating quadratic storage. Orthorhombic and
fully triclinic regression cases match the former dense minimum-image oracle.

A release-host 1000-atom microbenchmark measured approximately 4.76 s for the old
dense matrix versus 0.17 s for the adaptive neighbor-list diagnostic (~28x faster
for that sampled frame). This is diagnostic evidence, not a promised end-to-end NVE
speedup. Detailed ownership and equivalence requirements are recorded in
`docs/history/mlff/retired_specs/mlff_opt_verify1_verification_reuse_neighbor_scaling_spec.md`.

## OPT-CTRL1 - control-plane and telemetry cleanup - implemented in 0.20.103a0

`OPT-CTRL1` is implemented in mdstats 0.20.103a0 and completes the staged
optimization roadmap. It changes orchestration/runtime behavior only; the frozen MLFF
scientific compatibility identity remains 0.20.99a0 and the verification-case runtime
identity remains 0.20.85a0.

Campaign SQLite access now uses one persistent connection per calling thread rather
than reopening the database for every tiny lookup/write. Mutable SQLite connections
are never shared between threads. `get_payload_optional()` and
`get_record_optional()` provide one-query missing-record handling, and ordinary
`get_record()` restoration no longer performs the former second SQL fetch/JSON decode.
Naturally grouped parent-side state transitions can use `put_records()` to serialize
filesystem-backed payloads first and then commit their compact SQLite rows in one
transaction. Stage-state plus event publication is likewise one transaction.

Artifact authentication now has an optional durable restart cache at
`<workspace>/.mdstats/hash-receipts.sqlite3`. SHA-256 receipts are keyed by resolved
path, device, inode, byte size, nanosecond mtime, and nanosecond ctime. A complete
strong-stat identity match can reuse the previous digest after restart; any identity
change forces a byte hash, and the existing post-hash stat race check remains
binding. Receipt failures simply fall back to hashing and receipt pruning during
campaign compaction cannot affect scientific correctness.

GPU telemetry now prefers a process-persistent direct `libnvidia-ml`/NVML backend via
`ctypes`, caching device handles and avoiding a new `nvidia-smi` process for every
sample. `nvidia-smi` remains the fallback when NVML is unavailable. During the
five-minute evaluation/verification calibration, the original sampling cadence is
preserved. After calibration, the fixed GPU-utilization estimate is authoritative and
only the live VRAM hard guard needs telemetry, so polling defaults to 30 seconds via
`parallel_inference_post_calibration_monitor_interval_seconds`. A concurrency change
forces an immediate follow-up sample. Training telemetry is unchanged because its
admission controller still learns from live epoch-window observations.

Replay configuration-weight realization now streams ExtXYZ configurations through
ASE `iread()` and the high-precision writer instead of retaining the entire replay
corpus as an `Atoms` list. Campaign cleanup snapshots the top-level run-directory list
once and reuses it across active-child, obsolete-runtime, and checkpoint-model-cache
cleanup, while completed-preflight cleanup reuses one payload fetch.

Representative release-host microbenchmarks measured about 0.028 s for 3000 tiny
SQLite metadata reads with the persistent connection versus 0.687 s with one database
open per read (~24.5x lower connection overhead). Re-authenticating an unchanged 64
MiB artifact after clearing process-local hash state measured about 0.010 s from the
durable receipt versus 0.255 s for a fresh byte hash (~25.6x faster). These are
control-plane microbenchmarks, not end-to-end campaign speedup promises. Detailed
failure, compatibility, and qualification requirements are recorded in
`docs/specs/training_data/mlff_opt_ctrl1_control_plane_telemetry_spec.md`.


# Post-0.20.105 campaign evaluation, staged-precision, and storage-management roadmap

## Motivation and sequencing decision

The first production-scale campaigns exposed three practical limits after
`OPT-EVAL1` through `OPT-CTRL1` had removed the dominant reconstruction,
preparation, and control-plane overheads:

1. evaluating only four shortlisted epochs is inexpensive but provides weak coverage
   of a 30-epoch training history;
2. pure FP64 force training is prohibitively expensive on consumer GPUs even when
   checkpoint-bound preparation and inference remain tolerable, motivating an explicit
   FP32 -> FP64 refinement schedule rather than an implicit precision hack; and
3. retaining optimizer-bearing checkpoints and other campaign-owned intermediate
   artifacts can consume tens of gigabytes before a campaign is fully evaluated.

This is new profiling and operational evidence, so it opens a **new** staged roadmap;
it does not reopen or invalidate the completed `OPT-EVAL1`--`OPT-CTRL1` roadmap.
The evaluation policy is implemented first because storage reclamation must not delete
an artifact that the new evaluator may still need.

The binding implementation order is:

1. `EVAL-MF1` - nested multi-fidelity checkpoint evaluation core;
2. `EVAL-MF2` - conservative survivor control, reporting, and production-default
   qualification;
3. `PREC1` - precision profiles, explicit staged schedule, and `init`/TOML protocol
   realization;
4. `PREC2` - in-process precision-stage execution, optimizer/EMA promotion, and exact
   restart semantics;
5. `PREC3` - campaign-wide precision qualification, reporting, and profile activation;
6. `STOR1` - campaign storage accounting and ownership boundary;
7. `STOR2` - lossless completed-checkpoint compaction;
8. `STOR3` - automatic lifecycle-safe reclamation;
9. `STOR4` - manual tiered reclamation with explicit capability-loss reporting;
10. `STOR5` - immutable deduplication and optional cold archival.

No storage stage may weaken the source-ownership boundary, final-model retention, or
scientific lineage merely to reclaim disk space.

## EVAL-MF1 - nested multi-fidelity checkpoint evaluation core - implemented in 0.20.106a0

### Goal

Replace the current production dependence on a small fixed checkpoint shortlist with a
multi-round evaluator that examines **every saved epoch at low fidelity**, progressively
allocates more monitor labels to the most promising epochs, and performs the final
scientific decision only on full authoritative monitor data.

For a typical 30-epoch campaign the initial planned ladder is approximately:

```text
round 1: 30 checkpoints x 10% target monitor + 10% replay monitor
                         -> retain about one third
round 2: ~10 checkpoints x 33% target monitor + 33% replay monitor
                         -> retain a conservative finalist set
round 3: ~4-6 checkpoints x 100% target monitor + 100% replay monitor
                         -> authoritative admissibility and selection
```

The fractions, survivor fraction, and minimum finalist count are execution-policy
parameters and shall be configurable. The default ladder is a starting production
policy, not a scientific constant.

### Equal-fidelity target/replay invariant

At every partial round a fraction `f` means the same nominal fraction of **each**
authorized monitor domain:

$$
|T_r| \approx f_r |T|, \qquad |R_r| \approx f_r |R|.
$$

Target and replay data remain distinct scientific domains and retain their existing
metric meanings and checkpoint-policy roles; they are not pooled into one artificial
RMSE. However, the evaluator shall not allocate a systematically higher fidelity to
one domain than the other. Integer rounding and mandatory stratum minima may make the
realized counts differ slightly, but both domains use the same declared round fraction
and subset-construction rules.

For naive fine-tuning, where no replay monitor is part of the frozen protocol, the same
ladder applies to the target monitor alone.

### Deterministic nested monitor subsets

Each complete target/replay monitor obtains one immutable deterministic evaluation
order before any checkpoint result is visible. Round subsets are prefixes of that
order:

$$
T_1 \subset T_2 \subset \cdots \subset T_K=T,
\qquad
R_1 \subset R_2 \subset \cdots \subset R_K=R.
$$

The ordering shall preserve the monitor's declared condition/source structure rather
than sample correlated MD frames as iid observations. At minimum, construction must be
balanced over available condition axes, source/trajectory groups, and other frozen
monitor strata, with deterministic temporal spacing inside a source where applicable.
Subset construction is label-independent and must be frozen before candidate metrics
are inspected.

A `NestedCheckpointEvaluationPlan` (name provisional until implementation) shall bind:

- the complete target and replay monitor identities;
- the ordered frame/configuration identities in each domain;
- round fractions and realized counts;
- stratification and temporal-spacing policy;
- checkpoint survivor fraction and minimum finalist count;
- checkpoint metric/admissibility policy identities;
- numerical prediction contract, dtype, device, and acceleration identities required
  by the existing OPT-EVAL2/3 caches.

### Incremental prediction reuse

Nested rounds must be computationally incremental. If round 2 contains round 1, a
surviving checkpoint evaluates only the newly added configurations
`T_2 - T_1` and `R_2 - R_1`; round-1 predictions are reused exactly. The same rule
holds for every later round. Candidate prediction manifests therefore need an
append/extension contract keyed by complete-monitor identity, checkpoint/model SHA,
ordered configuration identity, and numerical inference contract.

Foundation-model predictions remain checkpoint-independent and reuse existing DATA6
or OPT-EVAL2 artifacts whenever their identities match. A larger round shall never
recompute a previously authenticated foundation or candidate prediction merely because
its evaluation fidelity increased.

### Screening versus scientific acceptance

Partial-round metrics are explicitly **screening evidence**. They may determine which
checkpoints receive more evaluation budget, but they may not:

- create a final `CheckpointAdmissibilityDecision`;
- satisfy a hard scientific threshold as final evidence;
- authorize model export or protocol freeze; or
- be represented as full-monitor metrics.

Only a checkpoint evaluated against the complete target monitor and, when required,
the complete true-label replay monitor may receive final admissibility and participate
in the authoritative `CheckpointSelectionRecord`.

The evaluator must retain at least a declared minimum number of full-fidelity finalists
(default target: four) unless fewer saved checkpoints exist. Final selection continues
to use the frozen DATA9B checkpoint policy; multi-fidelity evaluation changes **which
predictions are purchased**, not the scientific definition of the winning checkpoint.

### Restart and failure behavior

Every round shall commit:

- authenticated partial-prediction coverage;
- partial metric records tagged with round/fidelity identity;
- the survivor set and deterministic ranking inputs;
- reason codes for elimination or retention; and
- the exact unfinished delta for restart.

A crash after a partial round resumes from durable prediction coverage and must not
restart completed inference. Corrupt/missing partial artifacts are recomputed from the
last authenticated boundary. An unevaluated or partially evaluated checkpoint is never
silently treated as scientifically rejected.

### EVAL-MF1 acceptance gate

EVAL-MF1 is complete only when focused tests demonstrate:

1. deterministic, nested, stratified target and replay subsets under the same nominal
   fractions;
2. no monitor-label leakage into subset construction;
3. exact incremental prediction reuse between rounds;
4. restart/corruption recovery without duplicate inference of authenticated subsets;
5. all saved epochs entering round 1;
6. full target **and** full replay evaluation for every finalist in the final round;
7. no final admissibility/selection from partial metrics; and
8. numerical identity between a finalist's accumulated multi-round predictions and a
   direct one-shot full-monitor evaluation.

Detailed implementation requirements are recorded in the EVAL-MF specification under
`docs/specs/training_data/` (`mlff_eval_mf_successive_halving_spec.md`).

### EVAL-MF1 implementation record (0.20.106a0)

The implemented gate adds a public `MultiFidelityEvaluationPolicy`, deterministic
`MultiFidelityMonitorLadder` construction, explicit partial-round records, and
persistent prediction-coverage composition. The campaign evaluator accepts the
`checkpoint_strategy = "multi_fidelity"`. In 0.20.106a0 this remained opt-in; after
EVAL-MF2 qualification in 0.20.107a0 it becomes the generated default. Legacy configs
that omit the strategy retain the historical bounded fallback. All saved checkpoints enter round 1.
Target and true-replay monitors use the same declared round fractions, with
independent deterministic stratification/source/temporal orders. Later rounds infer
only newly added configuration identities and compose cumulative metrics from
authenticated immutable prediction shards.

Partial records are stored under dedicated multi-fidelity keys and carry the
`screening_partial` evidence class; they never populate the ordinary authoritative
`evaluation:<run>:<checkpoint>` namespace. Only final-round checkpoints evaluated on
the complete target and, where required, complete true-replay monitors produce the
existing `CheckpointEvaluationRecord` used by DATA9B selection. Screening survivor
records persist deterministic rank, metric inputs, retained/screened-out outcome, and
reason code for every candidate. Corrupt prediction shards are rejected and only the
affected subset is recomputed on restart.

The gate intentionally does **not** acquire new checkpoint-deletion authority.
Multi-fidelity screened-out checkpoints remain available until the later STOR stages
define qualified compaction/evaluation capsules. Focused synthetic, restart/cache,
true-label replay, and supplied MACE 0.3.16 regressions pass; EVAL-MF2 remains
responsible for guard-band survivor statistics, comprehensive epoch reporting,
exhaustive-comparison qualification, and migration to the generated default.

## EVAL-MF2 - conservative survivor control, diagnostics, and default migration - implemented in 0.20.107a0

EVAL-MF2 hardens the EVAL-MF1 nested evaluator and makes it the generated production
checkpoint strategy. The nominal one-third survivor fraction remains a resource target,
not a hard scientific cap. The implemented survivor controller uses paired source/temporal-
block evidence because every checkpoint is evaluated on the same configurations. At a
cutoff, a below-cutoff candidate is retained when its paired mean primary-metric excess is
no larger than a frozen guard equal to a 2% relative margin plus two standard errors over
at least four common blocks. With insufficient block evidence, the deterministic 2%
relative margin is used rather than pretending adjacent frames are iid samples.

For true-label replay campaigns, the controller additionally reserves up to the declared
minimum-finalist count of provisionally replay-compatible candidates, ranked by the same
frozen target primary metric. This prevents target-only screening from eliminating every
plausible replay-retaining checkpoint. Between partial rounds, pairwise rank inversion is
measured over common survivors; an inversion fraction of at least 25% expands the next
round to at least 50% of the current candidates rather than forcing an unstable one-third
prune. All thresholds are explicit `MultiFidelityEvaluationPolicy` fields and therefore
content-digested execution policy.

EVAL-MF2 also implements the comprehensive per-epoch campaign report. For every saved
epoch it merges MACE training-history target/replay metrics with every independent
multi-fidelity round, realized target/replay counts, energy/force/focus/worst-condition
metrics when available, replay degradation, survivor or elimination reasons, final
admissibility, and selected status. Normative JSON plus CSV and Markdown derivatives are
written under `results/<run-id>-epoch-evaluation.*`.

Qualification includes deterministic noisy-cutoff/rank-inversion/replay-rescue tests, a
representative 30-checkpoint exhaustive comparison, and supplied MACE 0.3.16 restoration/
graph-cache regressions. The representative 30-checkpoint case selects the same
true-replay-admissible epoch as exhaustive evaluation while purchasing 10.89 full-
checkpoint-equivalent nested candidate inference instead of 30, a 63.7% reduction for
that case. This is representative evidence, not a claim that every campaign receives the
same reduction or that the screen mathematically guarantees the global full-monitor
minimum over eliminated epochs.

With this gate closed, newly generated campaign TOML uses
`checkpoint_strategy = "multi_fidelity"`. The old `bounded` strategy remains an explicit
fast/compatibility mode, `exhaustive` remains the audit/reference mode, and legacy configs
that omit `checkpoint_strategy` retain bounded behavior for restart compatibility.
Partial-round evidence remains structurally incapable of authorizing final admissibility,
selection, protocol freeze, or checkpoint deletion; only full-fidelity finalist records
enter the existing DATA9B scientific selection path.


## PREC1 - precision profiles, explicit staged schedule, and init realization - implemented in 0.20.108a0

### Goal and user-facing profiles

PREC1 introduces a small user-facing precision choice while keeping the resolved
training arithmetic explicit and protocol-bound. The campaign initializer shall accept:

```text
mdstats-mlff-campaign init --precision single
mdstats-mlff-campaign init --precision double
mdstats-mlff-campaign init --precision refine
```

A plain `init` is equivalent to `--precision single` for backward-compatible,
throughput-oriented default behavior. The profile names are convenience inputs; all
scientific/runtime identity is bound to the fully resolved dtype and stage schedule.

The canonical generated profiles are:

- `single`: FP32 foundation/preparation, FP32 training throughout, FP32 evaluation,
  FP32 verification, and FP32 final export;
- `double`: FP64 foundation/preparation, FP64 training throughout, FP64 evaluation,
  FP64 verification, and FP64 final export; and
- `refine`: FP64 foundation/preparation, staged FP32 -> FP64 training, FP64 evaluation,
  FP64 verification, and FP64 final export.

`refine` is an economical FP64-refined protocol, **not** a claim that late FP64
refinement is scientifically equivalent to full-FP64 optimization. Its default training
schedule is 80% FP32 followed by 20% FP64. With the reference 30-epoch policy this
resolves to 24 FP32 epochs and 6 FP64 epochs.

The friendly names also control the existing critical-precision policy. Canonical
`single` must be genuinely single precision across profile-controlled model execution,
critical reductions/returned observables, evaluation, verification, and export; it may
not silently retain the historical critical-FP64 safety lock while presenting itself as
`single`. Canonical `double` and the non-training portions of `refine` remain FP64.
Legacy configurations that intentionally combine an FP32 model body with critical FP64
operations remain readable and reproducible, but they are a legacy/custom policy and
shall not be silently relabeled as canonical `single`.

### Generated TOML must expose the resolved policy

The initializer shall not hide staged behavior behind the profile name. The generated
TOML for `refine` shall contain an explicit editable schedule equivalent to:

```toml
[campaign]
precision_profile = "refine"

[model]
dtype = "float64"

[training]
max_num_epochs = 30
learning_rate = 1.0e-4

[training.precision]
mode = "staged"
minimum_final_stage_epochs = 3
minimum_final_stage_gradient_updates = 15000
preserve_optimizer_state = true
preserve_scheduler_state = true
preserve_ema_state = true

[[training.precision.stage]]
dtype = "float32"
fraction = 0.80
learning_rate_scale = 1.0

[[training.precision.stage]]
dtype = "float64"
fraction = 0.20
learning_rate_scale = 0.5

[evaluation]
dtype = "float64"

[verification]
dtype = "float64"

[export]
dtype = "float64"
```

The exact TOML surface may be normalized during implementation, but these semantics are
binding. `single` and `double` are represented by the same general schedule model with
one stage; `refine` uses two stages. Advanced users may edit the explicit stage list,
including additional stages, but any edit creates a distinct resolved training protocol.

### Fraction resolution and refinement floor

Stage fractions are resolved deterministically only after `max_num_epochs`, the DATA8
training exposure, batch size, and expected gradient-update count are known. Fractions
must be positive, ordered, and sum to one within a declared parsing tolerance. Integer
rounding residue is assigned deterministically so stage epochs sum exactly to the frozen
epoch budget.

For the canonical `refine` profile, the final FP64 stage must satisfy the declared
fraction plus a hard minimum of three full FP64 epochs. The 15,000-gradient-update value
is retained as a replay-calibrated reference floor. If it can be satisfied by extending
the final stage while retaining an earlier FP32 stage, the resolver does so. If it is
mathematically impossible for the exact canonical 80/20 profile but the nominal FP64
tail already satisfies the hard epoch floor (the default n512 target-only case), the
resolver preserves the explicit 80/20 split and records the achievable FP64 update floor
in the resolved protocol instead of collapsing nearly the whole run into FP64 or failing
DATA8. User-edited/custom schedules keep strict fail-closed update-floor semantics.

The 80/20 split and 0.5 refinement learning-rate scale are defaults, not scientific
constants. They remain editable and are part of protocol identity.

### Learning-rate semantics

At a stage boundary the final-stage `learning_rate_scale = 0.5` applies to the
**effective optimizer learning rate at the transition**, not blindly to the original
startup rate. The scheduler and optimizer learning-rate bookkeeping must be updated
coherently, and the transition may not cause an unintended learning-rate increase.
Explicit absolute stage learning rates may be supported later, but the generated
`refine` profile uses a relative scale so edits to the base learning rate preserve the
intended refinement relationship.

### Precision-policy identity

A new staged-precision policy record shall bind at least:

- requested profile (`single`, `double`, or `refine`);
- fully resolved ordered precision stages;
- stage fractions and resolved epoch/update boundaries;
- per-stage learning-rate scales;
- optimizer/scheduler/EMA preservation policy;
- foundation/preparation, critical-operation, evaluation, verification, and export
  dtypes; and
- MACE/CuEq/runtime compatibility identities needed by the existing DATA9 contracts.

`TrainingProtocolIdentity` shall depend on the resolved schedule rather than the profile
label alone. Thus two configurations both originating from `refine` but using 80/20 and
90/10 splits are distinct protocols. A user-edited schedule cannot reuse a freeze record
from the generated default merely because both retain `precision_profile = "refine"`.

### PREC1 acceptance gate

PREC1 is complete only when focused tests demonstrate:

1. plain `init` and `init --precision single` generate equivalent single-precision
   policies;
2. `single`, `double`, and `refine` generate the canonical pipeline dtypes above;
3. generated TOML exposes rather than hides the explicit staged schedule;
4. 30 epochs resolve deterministically to the canonical 24/6 refine split;
5. rounding and minimum-refinement floors are deterministic and fail closed when
   impossible;
6. profile or schedule changes alter training-protocol identity; and
7. legacy FP32/FP64 one-stage configurations remain readable and map losslessly onto
   the generalized precision-schedule representation.

Detailed requirements are recorded in
`docs/specs/training_data/mlff_staged_precision_profiles_spec.md`.

### PREC1 implementation closure (0.20.108a0)

The runtime now owns a generalized `PrecisionSchedulePolicy` plus a fully resolved
`ResolvedPrecisionSchedule`. Canonical `single`, `double`, and `refine` profiles are
emitted by `init --precision`, with plain `init` resolving to `single`. The default
`refine` schedule resolves 30 epochs to 24 FP32 plus 6 FP64 epochs and binds the
15,000-update/three-epoch refinement floors after DATA8 loader exposure is known. The
resolved epoch/update boundaries and non-training pipeline dtypes participate directly in
training-protocol identity. Legacy schedule-free protocols retain their historical bytes and
digests.

PREC1 deliberately does not perform the live dtype transition. Until PREC2/PREC3 are
qualified, preflight fails closed for multi-stage schedules and canonical single-profile
critical-FP32 execution, preventing either from being silently executed under the legacy
one-stage/critical-FP64 runtime.

### 0.20.118a0 DATA8 refinement-floor correction

Production qualification exposed a scale-dependence hidden by replay-sized tests: the
15,000-update reference floor exceeds the *entire* 30-epoch optimizer-step budget of a
default n512 target-only naive fine-tuning job. DATA8 therefore failed after loader
exposure even though the explicit 24-FP32/6-FP64 schedule already exceeded the hard
three-epoch refinement floor. The resolver now treats only that exact canonical reference
case adaptively: impossible reference-update enforcement preserves the nominal split and
binds the achievable update floor. Custom schedules remain strict. This release also
corrects `require_update_floor=False`, which previously still enforced the update floor
whenever `updates_per_epoch` happened to be supplied.

## PREC2 - in-process staged precision execution and restart correctness - implemented in 0.20.109a0

PREC2 implements the risky runtime boundary only after PREC1 freezes configuration and
identity semantics. The canonical `refine` transition occurs **inside the live training
process at an epoch boundary**. It shall not be implemented as a stop/relaunch of an
ordinary MACE checkpoint merely to change `default_dtype`.

At the FP32 -> FP64 boundary mdstats shall promote, as one atomic training-state
transition:

- all floating model parameters and floating model buffers;
- Adam/AMSGrad first moments, second moments, and maximum-second-moment state;
- EMA shadow parameters/state used by MACE training;
- any other floating optimizer-owned per-parameter tensors discovered by the qualified
  optimizer adapter; and
- the dtype-sensitive training/runtime state required by the selected MACE/e3nn/CuEq
  backend.

The LR scheduler trajectory is preserved. Optimizer parameter-group learning rates and
scheduler-held current/base LR state are transformed consistently according to the
stage learning-rate scale. Promotion must not leave stale FP32 floating state hidden
inside the optimizer/EMA runtime.

### Transition and checkpoint records

A durable `PrecisionStageTransitionRecord` (name provisional) shall record:

- run, fold, seed, and training-protocol identities;
- completed epoch and gradient-update boundary;
- source and destination stage identities/dtypes;
- pre/post model floating-state inventories;
- pre/post optimizer and EMA floating-state inventories;
- LR before and after the transition;
- scheduler-state identity;
- acceleration/backend identity; and
- checkpoint/state digests sufficient to prove the transition occurred exactly once.

Restart semantics are stage-aware. A restart checkpoint must carry or be accompanied by
enough mdstats-owned state to recover the current precision stage, resolved future
schedule, optimizer/AMSGrad state, scheduler state, and EMA shadow state exactly. If the
upstream MACE checkpoint format omits state needed for exact staged restart, mdstats must
persist an authenticated companion record or extend its checkpoint adapter; it may not
claim exact restart by reconstructing missing EMA/precision state heuristically.

Checkpoints before the switch remain valid FP32 checkpoints. Checkpoints after the
switch are uniformly FP64 in all floating model state. A restart immediately before,
at, or after the switch must neither duplicate nor skip the transition.

### PREC2 acceptance gate

PREC2 is complete only when focused and real-MACE tests demonstrate:

1. deterministic FP32 -> FP64 promotion of model, optimizer/AMSGrad, and EMA floating
   state;
2. no stale FP32 floating optimizer/EMA tensors after a refine transition;
3. coherent stage LR scaling without an unintended LR increase;
4. exact stage-boundary bookkeeping in epoch and gradient-update space;
5. uninterrupted versus interrupt/resume runs produce equivalent transition identity
   and numerically equivalent continuation within the frozen tolerance;
6. restart immediately on both sides of the stage boundary is idempotent;
7. MACE 0.3.16 plus the qualified e3nn/CuEq backend can execute the staged transition
   on an actual force-training graph; and
8. final `refine` model state after the staged training boundary is uniformly FP64 and remains compatible with the existing direct checkpoint evaluation/export paths.

### PREC2 implementation closure (0.20.109a0)

The runtime now installs a MACE-0.3.16-qualified epoch-boundary hook driven by the immutable DATA8 `ResolvedPrecisionSchedule`. At a staged boundary it promotes every floating model parameter/buffer, recursively promotes floating Adam/AMSGrad optimizer state, promotes EMA shadow state, switches floating minibatch data to the active model dtype while preserving integral graph indices, applies the destination learning-rate scale, and persists an authenticated `MacePrecisionStageTransitionRecord`.

MACE 0.3.16 raw training checkpoints are insufficient for exact staged continuation because they save EMA-averaged model bytes but not the live model/EMA shadow state. PREC2 therefore maintains one latest-only authenticated companion per active staged run. The companion stores the live model state, EMA state, stage/protocol identity, scheduler state, LR state, and the matching raw-checkpoint identity. A newer raw checkpoint without a matching companion is treated as an incomplete commit and is not selected for staged restart. This bounds companion storage to one checkpoint-equivalent live/EMA state rather than duplicating it for every epoch.

Restart initialization resolves the dtype of the resumable stage before MACE constructs the model, so FP64 post-transition checkpoints are never silently loaded into a newly constructed FP32 model. The transition is idempotent across restart and cannot be repeated or skipped.

Focused tensor-state tests demonstrate exact uninterrupted-versus-resumed continuation for model parameters, Adam/AMSGrad state, and EMA shadow state. A real MACE 0.3.16 force-training smoke crosses FP32 -> FP64 in-process, finishes with uniformly FP64 model parameters, applies the expected 0.5 LR scale, and writes the transition/companion evidence. Existing CuEq campaign/source-contract regressions remain clean; the supplied qualification environment contains no `cuequivariance`/`cuequivariance_torch`, so **real CuEq runtime execution remains a mandatory PREC3 production-activation check rather than a fabricated PREC2 claim**.

PREC2 did not itself authorize canonical staged profiles at campaign preflight; that activation/reporting/default-qualification work is completed by PREC3 in 0.20.110a0.

## PREC3 - campaign integration, qualification, and profile activation - implemented in 0.20.110a0

PREC3 integrates staged precision with the complete campaign only after the transition
mechanics are qualified.

The campaign shall report the requested profile and resolved schedule prominently at
`doctor`, `prepare`, `preflight`, `train`, evaluation, verification, and final result
surfaces. For example, a default refine run should state:

```text
precision profile: refine
preparation/evaluation/verification/export: float64
training stage 1: float32, epochs 0-23, LR scale 1.0
training stage 2: float64, epochs 24-29, LR scale 0.5
optimizer/scheduler/EMA state: preserved across stage transition
```

Evaluation and verification follow the profile's declared non-training dtype and are
independent of which stage produced a checkpoint. The final selected `refine` production
model and deployment artifact are FP64. Existing `MaceModelPrecisionRecord`, deployment-export, checkpoint-evaluation, and
committee-verification contracts remain authoritative. The DATA9A5a
`MaceCriticalPrecisionPolicy` must be generalized from its historical mandatory-FP64
setting into an explicit profile-bound critical-precision setting: FP32 for canonical
`single`, FP64 for `double` and for the non-training portions of `refine`. Historical
FP32-body/critical-FP64 protocols remain reproducible as legacy/custom policies rather
than being renamed.

### Qualification matrix

Before profile activation, bounded qualification shall cover at least:

- `single`: one-stage FP32 training/evaluation/verification/export;
- `double`: one-stage FP64 throughout;
- `refine`: canonical 80/20 staged training with FP64 non-training stages;
- a non-default staged split to prove schedule configurability;
- interruption/restart before and after the refine boundary; and
- both naive and multi-head replay training where feasible.

The qualification does **not** require `refine` to reproduce the same scientific RMSE
as `double`. That is an empirical model-quality question to be reported by the
multi-fidelity evaluator. Qualification requires correct arithmetic realization,
restartability, lineage, finite training/evaluation, and final artifact precision.

Once qualified, `single` remains the generated default for plain `init`; `double` and
`refine` remain explicit opt-in profiles. No hardware heuristic may silently change the
requested precision profile. The resolved staged schedule, not a friendly profile name,
is the binding scientific/runtime identity.

### PREC3 acceptance gate

PREC3 is complete only when:

1. the three profiles are exercised end to end through campaign preflight/training,
   checkpoint evaluation, export, and bounded verification;
2. all report/manifests expose the resolved schedule and observed model precision;
3. cache/restart identities distinguish all materially different precision schedules;
4. EVAL-MF partial/full records remain valid and correctly dtype-bound for checkpoints
   originating from either precision stage;
5. final refine artifacts are FP64 and selected production models remain covered by the
   existing verification gate; and
6. the generated `campaign.toml.example` and CLI user guide document the same defaults
   as the executable initializer.

Only after PREC3 is qualified may the storage roadmap rely on staged-precision
checkpoint lifetimes and dtype-specific capsule requirements.

### PREC3 implementation closure (0.20.110a0)

PREC3 activates the immutable precision profile across the complete campaign. Preparation, training, preflight, checkpoint evaluation, verification, and final result surfaces report the requested profile, its resolved epoch stages, critical-operation dtype, and non-training/export dtypes. `results/precision-profile.json` is the durable profile summary.

Runtime critical precision is policy-driven. Canonical `single` removes the historical ScaleShiftMACE critical-FP64 patch and executes profile-controlled critical operations in FP32. `double` and `refine` retain FP64 critical operations. Schedule-free campaigns keep the legacy FP32-body/critical-FP64 contract. The MACE training wrapper, real-MACE preflight, checkpoint evaluator, and bounded NVE verifier all consume the same DATA8/config-bound critical-precision policy.

EVAL-MF is precision-stage agnostic. Under an explicit profile, direct checkpoint reconstruction may cast the completed deployment architecture to the raw checkpoint state dtype; MACECalculator then converts the candidate to the evaluation dtype. This allows early FP32 and late FP64 refine checkpoints to be ranked under the same FP64 monitor contract without weakening the legacy dtype-mismatch fallback.

Explicit-profile target-head exports are routed through the existing exact deployment converter. A `refine` checkpoint selected from the FP32 portion is therefore promoted, reloaded, state-verified, and published as uniformly FP64; `single` publishes FP32 and `double` FP64. Deployment manifests preserve the conversion kind and exact-state evidence.

Real MACE 0.3.16/e3nn tests cover native single/double inference, FP32-candidate evaluation under FP64 refine evaluation, exact FP32-to-FP64 deployment conversion, and the PREC2 in-process staged force-training/restart transition. `cuequivariance` is not installed in the release qualification environment, so no fabricated real-CuEq execution evidence is claimed. CuEq production remains conditional on runtime availability and must pass the campaign's real-MACE preflight in the CuEq-enabled environment before training.

With PREC3 closed, staged-precision checkpoint lifetimes and dtype-specific storage roles are stable enough for STOR1.

## STOR1 - campaign storage accounting and ownership boundary - implemented in 0.20.111a0

Storage optimization begins with accounting and deletion authority, not deletion.
STOR1 shall inventory campaign artifacts by ownership, scientific/restart role,
reconstructability, and physical storage cost.

### Hard user-data boundary

**No campaign cleanup operation may delete, truncate, rewrite, rename, or move
user-supplied training/replay/true-label/source material from external directories.**
Those paths are read-only inputs even when referenced by campaign state.

A destructive operation is authorized only for an artifact that:

1. resides inside the resolved campaign-owned workspace or an explicitly created
   campaign-owned content store;
2. carries campaign ownership/provenance sufficient to explain why mdstats created it;
3. passes real-path containment checks without following a symlink escape; and
4. is not classified as a protected production/diagnostic artifact.

A path merely appearing in SQLite or a TOML file is not deletion authority.

### Storage report

A new storage-report surface shall summarize at least:

- logical bytes;
- allocated physical bytes where the platform exposes them;
- unique-inode bytes so hardlinks are not double-counted;
- artifact family and ownership class;
- automatic versus manual reclamation eligibility;
- restart/re-evaluation capability retained or lost by deletion; and
- the largest individual files/directories.

STOR1 is read-only with respect to reclamation. `mdstats-mlff-campaign storage report` (or bare `storage`)
walks the campaign workspace without following directory symlinks, writes
`results/storage-report.json` when that destination itself passes containment checks,
and reports logical bytes, inode-deduplicated allocated physical bytes, unique-inode
logical bytes, ownership/retention family, planned automatic/manual eligibility,
capability loss, and the largest files/directories.

Configured `training_root`, foundation model, replay train/monitor, true-label replay,
and the campaign configuration remain protected user/reference inputs even if a user
places one physically inside the workspace. A campaign-owned symlink may itself be
unlinked by existing cleanup when its parent is contained, but its external target is
never traversed or treated as owned.
STOR1 distinguishes link-object deletion authority from recursive traversal authority:
a contained symlink object can be removed, while a cleanup root is traversable only when
its resolved root is itself contained and does not overlap a protected input.

STOR1 also retrofits the same `CampaignOwnershipBoundary` into the pre-existing cleanup
and post-evaluation checkpoint-pruning code. A materialization/checkpoint path merely
stored in SQLite/JSON cannot authorize deletion outside the workspace; unsafe state DB,
runtime-record, diagnostic, or cleanup-report destinations fail closed. The acceptance
gate covers hardlinks, symlink escapes, configured inputs inside the workspace,
path-traversal/external materialization references, and preservation of existing safe
cache cleanup behavior.

## STOR2 - lossless completed-checkpoint compaction - implemented in 0.20.113a0

Optimizer-bearing MACE checkpoints dominate live campaign storage because Adam/AMSGrad,
scheduler, and related continuation state can exceed the deployable model state by a
large factor. STOR2 introduces an authenticated **evaluation state capsule** for completed,
nonselected checkpoints while keeping the scientific checkpoint identity anchored to the
original raw-checkpoint SHA-256.

The implemented lifetime is deliberately conservative:

```text
active/interrupted training:
    retain every required full restart-capable checkpoint

training complete, winner not yet selected:
    retain raw checkpoints; a model-only capsule cannot guarantee restart capability
    for a checkpoint that may still become the production winner

per-run evaluation/selection complete:
    retain the selected raw checkpoint + production model by default
    replace each qualified nonselected raw checkpoint with an authenticated
    model-state-only evaluation capsule
```

The capsule binds source checkpoint SHA-256, epoch/run lineage, immutable DATA8 MACE
configuration digest, reconstruction contract, model-state digest, and capsule byte
identity. Evaluation source resolution is representation-aware: OPT-EVAL1/OPT-EVAL4 may
consume the original raw checkpoint or the validated capsule while continuing to use the
original checkpoint SHA as scientific/cache identity. This preserves later true-label
refresh, checkpoint re-evaluation, and target-head reconstruction without retaining
optimizer continuation state for every rejected epoch.

Raw removal follows a strict transaction: verify raw source -> atomically write capsule ->
authenticate capsule -> reconstruct independently -> prove exact deployable-state match ->
commit/read-back the campaign capsule record -> re-authenticate -> delete the raw source
through the STOR1 ownership boundary. A capsule that is not smaller than the raw checkpoint
is rejected as a storage optimization. Corruption, unsupported checkpoint layout, missing
immutable DATA8 configuration, reconstruction mismatch, or ownership ambiguity all fail
closed to raw retention. Completed-run validation accepts the original immutable checkpoint
catalog represented by either raw checkpoints or authenticated capsules; rerunning `train`
does not retrain merely because STOR2 has compacted nonselected bytes.

Qualification includes a real MACE 0.3.16/e3nn model in which reconstruction from the raw
checkpoint and from the capsule produces exactly identical model state and energy, force,
and stress outputs. Existing multi-head/direct-restoration semantics are preserved by
reusing the qualified OPT-EVAL1 reconstruction path rather than inventing a separate model
loader. The selected production checkpoint remains full/restart-capable by default.
STOR2 does not authorize general cache/prediction cleanup; that begins at STOR3.

## STOR3 - automatic lifecycle-safe reclamation - implemented in 0.20.114a0

STOR3 extends the current conservative cleanup only where the dependency graph proves
that no user-visible scientific/restart capability is lost.

Automatic cleanup may reclaim campaign-owned garbage, superseded staging generations,
orphaned payloads, successful-preflight temporaries, reconstructable graph/view caches,
and other artifacts whose authoritative parents remain available. It may compact or
remove nonselected checkpoint state only under the completed-selection/capsule rules
qualified by STOR2.

The following are protected by default and are **not** automatic cleanup targets:

- all external user-supplied source/training/replay/true-label material;
- every final selected production model;
- the selected production raw checkpoint unless an explicit later archival policy says
  otherwise;
- campaign configuration and immutable protocol/selection/verification records;
- diagnostic text records, logs, training histories, and compact JSON/CSV summaries;
- any artifact still required to restart an incomplete stage; and
- any sole surviving evidence required to reconstruct current authoritative metrics.

Disk-pressure handling shall run safe reclamation before interrupting active children,
but it may never cross the protected classes merely to satisfy a free-space threshold.
Every automatic cleanup appends an authenticated JSONL event to `results/cleanup-manifest.jsonl` containing removed paths, bounded pre-deletion filesystem identities, reasons, bytes reclaimed, retained capabilities, and an explicit empty capability-loss set. The manifest is itself guarded by the STOR1 ownership boundary.

The implemented policy additionally reclaims the reconstructable OPT-EVAL3 graph/view cache only after authoritative evaluation is complete; it does not automatically remove DATA6/model-sweep predictions, evaluation-prediction shards, or true-label replay artifacts. Under low-disk pressure, training invokes this STOR3 safe policy before interrupting children. Active run roots are excluded; interruption occurs only if safe reclamation cannot restore the configured free-space reserve.

## STOR4 - manual tiered reclamation with capability-loss reporting - implemented in 0.20.115a0

Some large artifacts are valuable but not essential to the final production model.
STOR4 introduces explicit user-selected retention tiers rather than treating all such
artifacts as either permanent or disposable.

The implemented hierarchy is:

| Tier | Typical artifacts | Default consequence |
|---|---|---|
| `safe` | garbage, stale staging, superseded runtime payloads | no scientific/restart capability loss |
| `cache` | graph/view/frame/hash caches | recomputation becomes slower |
| `recompute` | expensive DATA6/evaluation prediction caches when reconstructable | later reselection/re-evaluation may require expensive inference |
| `compact` | nonproduction checkpoints/models and cold materializations after freeze | exact continuation or cheap alternative-model recovery may be lost |
| `archive` | explicitly selected cold reproducibility material | retained only in a verified archival representation |

The implementation keeps these tiers cumulative and explicit. `storage cleanup --tier safe` uses only lifecycle-safe reclamation; `cache` additionally removes reconstructable acceleration caches. `recompute` may remove DATA6/model-sweep, evaluation-prediction, and verified true-label replay materializations after the required downstream stages complete and only while configured reconstruction inputs still exist. `compact` requires full verification, a protocol freeze, and a protected exported production model before it may remove nonselected evaluation capsules, nonproduction per-run model copies, or hot DATA7/DATA8 materializations.

Every invocation first emits and writes `results/manual-reclamation-plan-<tier>.json`. `recompute` and `compact` do not apply unless `--apply` is explicit. With STOR5, `storage cleanup --tier archive --apply` additionally requires successful archive creation, independent member verification, and a committed archive receipt before consequential hot deletion. Diagnostic text/log records remain retained at every tier. External inputs, workspace production models, selected production raw checkpoints, and campaign protocol/selection/verification records are never STOR4 deletion candidates.

The capability report covers training restart, exact checkpoint re-evaluation, metric-only recomputation, DATA7 reselection, DATA8 rematerialization, current production inference, and verification replay. It distinguishes fully preserved capability from capability that remains possible only after reinference/rematerialization. Intentional higher-tier capability losses are appended to `results/cleanup-manifest.jsonl`; STOR3 automatic events retain the stricter empty-loss contract.

## STOR5 - immutable deduplication and authenticated cold archival - implemented in 0.20.116a0

STOR5 implements two optional physical-storage optimizations while preserving the
scientific checkpoint/model/data identities frozen by the earlier gates.

`storage deduplicate` is plan-only by default and requires completed verification plus an
authoritative protocol freeze. It scans only known campaign-owned immutable families
(DATA7/DATA8 materializations, qualified scientific/reconstructable caches,
nonselected evaluation capsules, nonproduction run models, and checkpoint-model
caches). Exact byte duplicates are grouped by SHA-256. With `--apply`, a canonical
object is materialized under `.mdstats/content-store/sha256/<prefix>/<digest>` and
same-filesystem duplicates are atomically replaced by hardlinks to that object. Active
checkpoints, SQLite state, logs, production models, selected raw checkpoints, and every
configured external input are excluded. Symlinks are never followed. STOR1 accounting
continues to report logical bytes separately from inode-deduplicated physical bytes.

Cold archival is available independently through `storage archive create`, `storage archive verify`, and
`storage archive restore`, and is integrated into `storage cleanup --tier archive --apply`. Only
consequential STOR4 `recompute`/`compact` actions require archival; disposable `safe`
and `cache` material does not. The archive is a self-contained `tar+gzip` object under
`.mdstats/cold-archive/` with workspace-relative members, SHA-256/size/mode for every
file, an authenticated manifest-content digest, and an archive SHA-256. Hardlinked hot
files are dereferenced into ordinary archive members so a later restore does not depend
on the content store.

The destructive order is binding and fail-closed: emit the STOR4 capability plan; apply
any independently lossless STOR2 nonselected-checkpoint compaction; recollect the exact
post-STOR2 archive roots; create the archive; independently read back and hash every
member; persist the archive receipt in campaign state; only then remove the represented
hot roots. The cleanup audit changes those actions from irreversible capability loss to
`archive_restore_available=true` with the archive identity attached. Archive creation,
member verification, receipt persistence, or ownership failure leaves consequential hot
bytes in place.

`storage archive restore` re-verifies both manifest and archive, reconstructs members beneath a
campaign-owned staging tree, authenticates every staged file, preflights all hot
destinations, refuses conflicting existing content, atomically installs missing files,
and hashes the final layout again before writing a restore receipt. `storage archive verify` is
read-only. Orphan content-addressed objects whose last hot hardlink has disappeared are
pruned after reclamation so earlier deduplication cannot pin deleted hot bytes on disk.

STOR5 is optional for users but fully implemented. It closes the post-0.20.105
EVAL-MF/PREC/STOR roadmap; no further gate is required by this roadmap.

## New-roadmap completion rule

Each gate is specified, implemented, and tested independently. In addition to the
existing optimization completion rules, this roadmap requires:

1. **evaluation fidelity is explicit** - partial metrics can never masquerade as full
   acceptance evidence;
2. **target/replay fidelity is symmetric** - the same round fraction is applied to
   both when replay exists;
3. **nested work is reused** - later evaluation rounds extend rather than redo earlier
   authenticated inference;
4. **precision profiles are explicit** - `single`, `double`, and `refine` resolve to
   visible dtype/schedule policies rather than hidden runtime behavior;
5. **refinement is a real optimizer continuation** - staged FP32 -> FP64 promotion
   includes optimizer/AMSGrad and EMA state plus exact restart semantics;
6. **cleanup is ownership-scoped** - external user files are structurally outside the
   deletion authority;
7. **the production result is protected** - final selected models and default
   diagnostics/logs survive ordinary cleanup; and
8. **capability loss is explicit** - any manual higher-tier reclamation states exactly
   what can no longer be restarted, recomputed, or re-evaluated cheaply.

`EVAL-MF1` is implemented in 0.20.106a0, `EVAL-MF2` in 0.20.107a0, `PREC1` in 0.20.108a0, `PREC2` in 0.20.109a0, `PREC3` in 0.20.110a0, `STOR1` in 0.20.111a0, `STOR2` in 0.20.113a0, `STOR3` in 0.20.114a0, `STOR4` in 0.20.115a0, and `STOR5` in 0.20.116a0. The post-0.20.105 evaluation, precision, and storage implementation roadmap is complete.
Storage implementation does not begin until EVAL-MF and staged-precision work establish
the checkpoint, prediction, optimizer-state, and dtype lifetimes that storage policy
must respect.

# Post-0.20.120 adaptive-training, binary-precision, and evaluation-simplification roadmap

**Status:** architecture recorded in `mdstats 0.20.121a0`; `ADAPT-PREC1` is implemented
in `mdstats 0.20.122a0`, `ADAPT-MON1` in `mdstats 0.20.123a0`, `ADAPT-STOP1` in
`mdstats 0.20.124a0`, `ADAPT-RANK1` in `mdstats 0.20.125a0`, `ADAPT-EVAL1` in
`mdstats 0.20.126a0`, `ADAPT-VERIFY1` in `mdstats 0.20.127a0`, and `ADAPT-MIGRATE1` in
`mdstats 0.20.128a0`. The seven-gate adaptive revision is complete.
Binary learned-model precision, fixed common online monitors, criterion-driven training
termination, and top-K full evaluation now supersede the corresponding legacy production
semantics for new campaigns. EVAL-MF remains readable and explicitly selectable only for
historical/pre-adaptive configurations.
Historical EVAL-MF/PREC records remain valid evidence for the campaigns that created
them and are not rewritten retrospectively.

## Motivation and evidence

Production profiling after the first FP32/FP64 campaigns changed three assumptions on
which the earlier EVAL-MF/PREC design was based.

1. **Model precision is not the dominant observed accuracy variable.** On the common
   replay monitor, FP32 and FP64 learning trajectories are nearly coincident, whereas
   target validation errors move substantially with fold/condition composition. The
   useful precision choice is therefore the learned-model dtype itself, not an assumed
   FP32 -> FP64 refinement benefit.
2. **A small, deliberately constructed target monitor is already statistically sharp.**
   On the supplied 27-trajectory LTA regression, a 256-configuration
   trajectory/condition/time-balanced target monitor had a force-RMSE 95% resampling
   half-width of about `0.33 meV/A`, compared with a full balanced reference near
   `34.20 meV/A`. A 280-frame ordinary-random monitor was roughly twice as noisy.
3. **Replay is more heterogeneous but still suitable for fixed trend monitoring.** A
   512-configuration replay subset had a force-RMSE 95% random-subset half-width of
   about `2.7 meV/A`; therefore it is suitable as a fixed epoch-to-epoch forgetting
   monitor but not as authoritative final replay evidence.

The old production evaluator assumed a fixed approximately 30-checkpoint trajectory and
therefore bought additional 10% -> 33% -> 100% inference to discover promising epochs.
The new training loop already computes one target and replay monitor metric after every
epoch and may terminate anywhere before the 30-epoch ceiling. Repeating partial
inference in EVAL-MF would therefore duplicate work rather than reduce it.

The new cycle makes the following decisions binding *after implementation*:

- `precision = single|double` describes only learned-model arithmetic and model
  inference dtype;
- staged `refine` training and a user-facing `mixed` model mode are retired;
- mdstats-owned scientific reductions, fitting, statistics, and persistent simulation
  bookkeeping remain FP64 invariants rather than precision-profile choices;
- training ends when enough target adaptation has been demonstrated, when replay
  forgetting has clearly exceeded its useful region, or when the 30-epoch ceiling is
  reached;
- monitor metrics already paid for during training perform lightweight candidate
  screening; and
- only a small campaign-wide finalist set receives authoritative full evaluation.

## Ordered implementation sequence

The gates are implemented in this order:

1. `ADAPT-PREC1` - binary model-precision contract and removal plan for staged refine;
2. `ADAPT-MON1` - fixed-budget common target/replay monitor construction and evidence;
3. `ADAPT-STOP1` - weight-coupled target/replay thresholds and criterion-driven training;
4. `ADAPT-RANK1` - zero-new-inference epoch scoring and one champion per independent run;
5. `ADAPT-EVAL1` - retire EVAL-MF production screening and perform top-K full evaluation;
6. `ADAPT-VERIFY1` - full-evaluation/verification precision propagation and final selection;
7. `ADAPT-MIGRATE1` - schema/restart/storage migration, historical readability, and campaign qualification.

The sequencing is deliberate. Precision semantics must be frozen before they enter new
training/evaluation identities. Monitor roles must be frozen before stopping or ranking
can use them. Training must emit complete lightweight evidence before the evaluator can
eliminate duplicate partial inference. Compatibility cleanup is last so no historical
checkpoint or evaluation artifact becomes unreadable during the transition.

## ADAPT-PREC1 - binary model precision and invariant FP64 scientific arithmetic

**Status:** implemented in `mdstats 0.20.122a0`.

### User-facing model precision

The generated campaign interface shall support exactly two model precision choices:

```text
single  -> FP32 learned model, FP32 training/autograd, FP32 MACE model inference
double  -> FP64 learned model, FP64 training/autograd, FP64 MACE model inference
```

Plain `init` continues to select `single` unless the user explicitly requests `double`.
The words `refine` and `mixed` cease to denote supported production model-precision
profiles. No hardware heuristic may silently choose or alter model precision.

The model dtype follows the checkpoint through every operation that executes the learned
model:

- training forward/backward and optimizer state;
- epoch target-monitor inference;
- epoch replay-monitor inference;
- full target and replay evaluation inference;
- verification/NVE force inference;
- committee/member inference; and
- final exported model parameters and buffers.

An FP32 checkpoint must not be cast to FP64 merely to evaluate it under a common dtype,
and an FP32 checkpoint selected for production must not be published as an FP64 model.
Likewise, `double` checkpoints remain FP64 through evaluation and export.

### Hard FP64 scientific-arithmetic invariant

Model precision does **not** control mdstats-owned numerical analysis. Cheap operations
whose accuracy can benefit from wider arithmetic remain unconditionally FP64, including:

- elemental/reference-energy fitting and rank/SVD diagnostics;
- feature centering, scaling, PCA/QR/SVD, and selection-distance reductions;
- cell determinants, inverses, strain/polar-decomposition calculations, and geometric
  diagnostics;
- SSE/RMSE/MAE accumulation, confidence intervals, regression, and checkpoint scores;
- observable analyses such as MSD/VACF/VDOS/diffusion/conductivity and NVE drift fits;
- committee/statistical aggregation after model predictions leave the learned-model
  arithmetic boundary; and
- persistent MD positions, cell, velocities/momenta, and integrator bookkeeping where
  mdstats owns those arrays.

This is not called a `mixed` model. For `single`, FP32 model outputs may be converted to
FP64 before mdstats-owned reductions/statistics; that conversion prevents additional
analysis roundoff but does not claim FP64 model accuracy. Operations inseparable from the
MACE differentiation graph remain in the selected model dtype.

### Precision identity and migration boundary

`TrainingProtocolIdentity`, checkpoint identity, inference cache identity, evaluation
records, verification records, and exported-model manifests shall bind only the resolved
model dtype (`float32` or `float64`) plus the normal backend/dependency identities. The
resolved staged-precision schedule ceases to be a production identity field for new
campaigns.

Historical `refine` campaigns remain readable. A new campaign/configuration that still
requests `refine` must fail closed with an explicit migration message asking the user to
choose `single` or `double`; it must never be silently reinterpreted. An already-running
legacy staged campaign may be inspected/archived under historical compatibility code but
is not converted in place into a binary-precision scientific identity.

### ADAPT-PREC1 acceptance gate

The gate closes only when tests prove that:

1. `init` emits only `single|double` model precision choices;
2. `single` and `double` preserve exact model dtype through training, all inference,
   verification, and export;
3. no evaluator silently dtype-promotes one model class into the other;
4. FP64 scientific reductions remain FP64 under both model modes;
5. legacy `refine` evidence remains readable but cannot seed a silently reinterpreted
   new protocol; and
6. the retired schedule/optimizer-promotion machinery is no longer reachable from new
   production configurations.

### ADAPT-PREC1 implementation record (`0.20.122a0`)

The production initializer now accepts only `--precision single|double`; plain `init`
resolves to `single`. Generated TOML no longer writes a `[training.precision]` staged
schedule. Instead, `[model].dtype`, `[training].dtype`, `[evaluation].dtype`,
`[verification].dtype`, and `[export].dtype` are required to agree with the selected
learned-model precision. Any mismatch fails closed before production work begins.

New DATA8/optimizer identities are therefore schedule-free and cannot reach the PREC2
FP32-to-FP64 optimizer/EMA promotion runtime. The historical precision-schedule classes
and deserializers remain available only so old staged campaign evidence can be inspected
and archived. A historical `refine` profile is reported as read-only historical metadata;
production `prepare`, `preflight`, `train`, `evaluate`, and `verify` reject it with an
explicit migration message rather than reinterpreting it.

For both `single` and `double`, mdstats-owned critical/scientific arithmetic resolves to
FP64. This includes the qualified critical energy/virial reduction policy where it is
applicable and the existing NumPy/SciPy statistical/linear-algebra analysis paths. That
policy does not change the learned-model dtype: `single` model forward/inference remains
FP32 and `double` remains FP64. Evaluation checkpoint reconstruction explicitly disables
checkpoint/template dtype casting, and verification/export inherit the checkpoint model
dtype rather than a separate evaluation/deployment precision.

Focused ADAPT-PREC1 qualification covers binary CLI generation, exact dtype propagation,
no silent evaluator promotion, invariant FP64 critical arithmetic, historical staged
readability/fail-closed production migration, and schedule-free DATA8 construction. The
legacy staged-schedule API remains regression-tested as historical compatibility, not as
a reachable new-campaign runtime.

## ADAPT-MON1 - fixed-budget common online monitors

**Status:** `implemented` in `mdstats 0.20.123a0`.

### Target monitor

The production default target online monitor contains:

```text
256 configurations
```

selected deterministically from the fixed representative DATA5 outer-monitor validation
domain. Selection must balance declared condition/material-profile strata and spread
samples across trajectory time. For the LTA profile this means, where available,
coverage across composition, temperature, strain/geometry condition, trajectory/source,
and the time axis within each trajectory.

The monitor is **common across competing folds/seeds/protocol-equivalent runs** so its
lightweight scores are directly comparable. This replaces the current production use of
fold-dependent monitor sizes such as 280 versus 1400 configurations. DATA5's held-out
evaluation folds remain independent evidence and never control checkpoint choice.

The 256 default is evidence-based rather than arbitrary: the supplied LTA convergence
study found a trajectory/time-balanced 256-frame force-RMSE 95% half-width of roughly
`0.33 meV/A`, well below the several-meV acceptance margins used for stopping.

### Replay monitor

The production default replay online monitor contains:

```text
512 configurations
```

from **true-label replay evidence**, not foundation pseudo labels. It must be fixed for
the campaign and selected with the strongest available chemical/structural/size coverage
stratification. It is nested within the replay model-selection/evaluation domain and is
used only for stopping/ranking; the authoritative full replay metric is still purchased
later on the full declared true-label replay evaluation corpus.

Using true labels gives the online replay RMSE and final replay RMSE the same physical
meaning. Pseudo-label replay remains valid gradient-training data, but pseudo-label
self-agreement is not the quantity against which the new absolute replay threshold is
applied.

### Monitor identity and uncertainty evidence

Every monitor record binds:

- parent evidence domain identity;
- exact selected configuration identities and order;
- requested and realized size;
- stratification policy and seed/random-start identity;
- label-domain and replay true-label lineage;
- independence/role grades inherited from DATA5; and
- monitor-size qualification evidence or a declared fallback when the requested
  stratification is infeasible.

The default sizes are policy values, not immutable scientific constants. Users may
change them, but doing so changes the training/checkpoint policy identity.

### ADAPT-MON1 acceptance gate

The gate closes only when:

1. all competing production runs consume the same target-monitor identity;
2. target monitor size defaults to 256 and replay to 512;
3. target sampling is condition/trajectory/time balanced rather than first-N or ordinary
   unqualified random sampling;
4. replay online metrics use true labels;
5. monitors never supply gradients;
6. held-out/locked evidence cannot leak into the monitor role; and
7. deterministic regeneration and corruption/restart tests reproduce exactly the same
   monitor memberships.

### ADAPT-MON1 implementation record - 0.20.123a0

The gate is implemented by the identity-bearing `OnlineMonitorPolicy` and
`OnlineMonitorRecord` contracts. New campaign preparation resolves an independent
true-label replay source before DATA7/DATA8 materialization and binds the policy into the
production materialization plan, DATA8 bundle, and per-job training-protocol identity.
The generated TOML defaults are `online_target_monitor_configurations = 256`,
`online_replay_monitor_configurations = 512`, and `online_monitor_seed = 161803`.

Target membership is selected once per label domain from DATA5 `outer_monitor` units.
The selector balances condition/run strata, then uses a deterministic random-start
systematic sample within each stratum so selected frames are spread across trajectory
time. Every final/fold job receives the exact same target-valid membership and therefore
the same target-monitor artifact content digest. Fold-specific held-out evaluation units
and locked interpolation tests remain excluded. If the parent outer-monitor domain is
smaller than the requested budget, all available frames are used and the fallback is
recorded explicitly rather than silently changing the policy.

Replay membership is selected only from a `TRUE_DFT` replay-monitor source. The selector
uses a stable chemistry/composition, atom-count/size-bin, and source-order key followed by
a deterministic systematic sample. The selected subset is materialized as
`shared/replay/online_true_replay_monitor.xyz`, re-inspected, and byte/geometry/label
lineage checked against the parent true-label artifact. In multi-head jobs this file is
used as MACE `pt_valid_file`; replay gradient training continues to use the configured
training replay corpus, including foundation pseudo labels where requested. Naive jobs
carry the same replay monitor evidence for the later ADAPT-STOP1 external epoch monitor,
but it is not injected as gradient data.

Monitor identities bind parent evidence, requested/realized sizes, exact ordered
memberships, source indices, stratification counts, strategy, seed, and label mode. Plan
and DATA8 schema revisions retain v1/v2/v3 historical readability, while new protocol
records bind the target record, replay record, replay-valid artifact, and monitor-policy
digests together. Focused qualification verifies deterministic regeneration, true-label
materialization, common target membership across all jobs, no target-training/replay-
monitor exact-geometry overlap, serialization/corruption rejection, and legacy schema
compatibility.

ADAPT-MON1 itself only freezes monitor evidence. Beginning in 0.20.124a0, ADAPT-STOP1
consumes those common monitor rows to terminate training at the target-success,
replay-exhaustion, or hard-epoch boundary. EVAL-MF remains runtime-authoritative until
ADAPT-EVAL1 closes.

## ADAPT-STOP1 - weight-coupled acceptance region and adaptive training termination

**Status:** implemented in `mdstats 0.20.124a0`.

### Full target threshold

Introduce an explicit global full-evaluation target force criterion:

$$
T_{\max}=30\ \mathrm{meV}/\text{\AA}=0.030\ \mathrm{eV}/\text{\AA}
$$

by default. This criterion is distinct from existing focus-group, energy, stress, and
worst-condition safety gates, which remain separate acceptance constraints.

### Score weights and derived replay threshold

Let positive target and replay score weights be $w_T$ and $w_R$. With replay enabled,
the default is

$$
w_T:w_R=1:1.
$$

Define the replay force-RMSE ceiling by equal weighted contribution at the two acceptance
boundaries:

$$
R_{\max}=\frac{w_T}{w_R}T_{\max}.
$$

Examples for $T_{\max}=30\ \mathrm{meV}/\text{\AA}$ are:

| Target:replay weight | $R_{\max}$ |
|---:|---:|
| 1:1 | 30 meV/A |
| 2:1 | 60 meV/A |
| 3:1 | 90 meV/A |
| 1:2 | 15 meV/A |

When replay is enabled both weights must be finite and strictly positive. A no-replay
protocol omits replay scoring/stopping entirely rather than using a zero-weight
singularity.

Before training, the campaign evaluates or loads the foundation model's true-label
replay baseline. If the derived $R_{\max}$ is already below that baseline, the policy is
asking the fine-tuned model to outperform the foundation model on replay. Preparation or
preflight must flag this explicitly and require a deliberate override rather than
silently treating the threshold as ordinary retention.

### Candidate region and stop margins

A saved epoch is lightweight-eligible only when

$$
T_{\mathrm{mon}}\le T_{\max}
\quad\text{and}\quad
R_{\mathrm{mon}}\le R_{\max}.
$$

Training does **not** stop immediately at those acceptance boundaries. It explores a
conservative margin around the useful tradeoff region and stops after an epoch when the
first of the following becomes true:

$$
T_{\mathrm{mon}}\le f_T T_{\max},\qquad f_T=0.80,
$$

or

$$
R_{\mathrm{mon}}\ge f_R R_{\max},\qquad f_R=1.20,
$$

or the hard epoch ceiling is reached:

```text
maximum epochs = 30
```

For the default 1:1 policy this gives:

```text
target candidate boundary : 30 meV/A
target successful stop     : 24 meV/A
replay candidate boundary  : 30 meV/A
replay exhaustion stop     : 36 meV/A
```

The stopping epoch itself need not be the selected checkpoint. A replay-exhaustion stop
may still leave an earlier admissible epoch that becomes the run champion. If no saved
epoch ever satisfies both candidate boundaries, the run ends with an explicit
`no_lightweight_admissible_checkpoint` outcome rather than pretending that the final
epoch is selectable.

The 0.80/1.20 factors are generated defaults and editable policy values. They are large
relative to the observed target monitor sampling error and intentionally bias mistakes
toward extra training rather than premature final acceptance.

### Other training-time checks

Energy, stress, focus-group, worst-condition, finiteness, and runtime-health diagnostics
continue to be recorded. The early-stop trigger is intentionally controlled by the
force-RMSE target/replay policy unless another existing hard safety condition terminates
the job. Ordinary non-monotonic one-epoch fluctuations are allowed; the implementation
must not assume mathematically monotone learning curves.

### ADAPT-STOP1 acceptance gate

The gate closes only when tests cover:

1. target stop at `0.80*T_max`;
2. replay stop at `1.20*R_max`;
3. the 30-epoch hard ceiling;
4. weight-derived replay thresholds for at least 1:1, 2:1, and 1:2;
5. preservation of earlier admissible checkpoints after a later replay-exhaustion stop;
6. explicit failure when no admissible epoch exists;
7. exact restart without losing already-computed epoch monitor metrics or changing stop
   semantics; and
8. foundation-baseline feasibility warnings/overrides for unusually replay-heavy weights.


### ADAPT-STOP1 implementation record (`0.20.124a0`)

New campaign preparation binds an immutable `AdaptiveTrainingStopPolicy` into DATA8,
production-materialization, and training-protocol identities. The generated defaults are
`T_max=0.030 eV/A`, `w_T:w_R=1:1`, `f_T=0.80`, `f_R=1.20`, and a 30-epoch hard ceiling.
The replay ceiling is derived rather than independently specified, so the default geometry is
30/24/30/36 meV/A for target candidate/target stop/replay candidate/replay stop.

MACE 0.3.16 performs the stop decision inside the qualified mdstats training-loop patch.
The common ADAPT-MON1 target and true-label replay validation rows are already paid for by
normal epoch validation; mdstats parses those rows without launching additional inference.
Before epoch 0, the initial true-label replay row freezes the foundation replay baseline and
fails closed when the derived replay ceiling is below that baseline unless the explicit
`allow_replay_threshold_below_foundation_baseline` override is set.

After each epoch's validation and durable save-all checkpoint, mdstats appends the target/replay
force RMSE, candidate eligibility, and any terminal reason to
`adaptive_training_stop.json`. The MACE loop then exits cleanly for `target_success`,
`replay_exhaustion`, `target_success_and_replay_exhaustion`, or `max_epochs_reached`; the
normal MACE final-model path still executes. A terminal run records whether at least one earlier
checkpoint is lightweight-admissible, but ADAPT-STOP1 does **not** rank or select that checkpoint.
That responsibility remains ADAPT-RANK1.

Restart semantics are fail-closed. Existing checkpoints require matching adaptive-stop state.
Repeated epoch evidence is idempotent and changed metrics are rejected. If a parent process is
interrupted after terminal stop evidence is durable but before final-model publication,
`--restart_latest` observes the terminal state, skips the epoch loop, and completes MACE's normal
finalization without training an additional epoch. Historical pre-ADAPT-STOP1 protocols remain
readable and continue their original fixed-epoch semantics.

## ADAPT-RANK1 - zero-new-inference lightweight ranking and one champion per run

**Status:** implemented in `mdstats 0.20.125a0`.

Training already paid for $T_{\mathrm{mon}}$ and $R_{\mathrm{mon}}$ at every epoch.
ADAPT-RANK1 therefore performs no new model inference. For every lightweight-admissible
epoch define

$$
S_{\mathrm{light}}
=
\frac{w_T T_{\mathrm{mon}}+w_R R_{\mathrm{mon}}}{w_T+w_R}.
$$

Because both quantities are force RMSE in the same units, the default 1:1 score is the
simple arithmetic mean. The score is a *ranking objective*, never a mechanism for
compensating a failed hard boundary.

Each independent run contributes exactly one lightweight champion:

$$
c_r=\arg\min_{e\in\mathcal A_r}S_{\mathrm{light}}(r,e),
$$

where $\mathcal A_r$ is that run's admissible-epoch set. This prevents a single fold from
occupying the campaign finalist list with several adjacent epochs. Deterministic ties
are resolved by lower target RMSE, then lower replay RMSE, then earlier epoch, then
stable checkpoint identity.

The run report shall preserve the full epoch trajectory, stop reason, candidate-region
entry, target/replay boundaries, score weights, all eligible epochs, and the chosen run
champion. A later full-evaluation failure never rewrites these training-time facts.

### ADAPT-RANK1 acceptance gate

The gate closes only when:

1. lightweight ranking performs zero additional MACE inference;
2. only epochs satisfying both monitor boundaries are score-eligible;
3. one and only one champion is emitted per independent run that has at least one admissible epoch; a run with no admissible epoch emits an explicit no-champion outcome;
4. ties are deterministic;
5. scores from different runs are comparable because they share common monitor
   identities; and
6. restart/reconciliation can regenerate the same champion from persisted epoch metrics
   without opening model checkpoints.

### ADAPT-RANK1 implementation record (`0.20.125a0`)

Successful adaptive training now derives `lightweight_run_champion.json` directly from the
terminal ADAPT-STOP1 state and the already-frozen checkpoint catalog. The ranking function accepts
no model path and performs no inference or checkpoint deserialization. It rechecks the target/replay
candidate boundaries under the frozen stop policy, requires exact stop-history/catalog epoch
coverage, and binds the common ADAPT-MON1 target/replay monitor identities into the ranking record.

Eligible checkpoints are ordered by weighted target/replay force-RMSE score, then target RMSE,
replay RMSE, earlier epoch, and checkpoint SHA-256. A canonical score comparison removes only
sub-femtoscale binary-representation noise before tie breaking. The full unrounded FP64 score is
retained in evidence. Runs with no admissible epoch persist
`no_lightweight_admissible_checkpoint` rather than selecting the terminal epoch.

The ranking artifact is immutable and content-addressed against the run plan, training protocol,
adaptive-stop policy/state, checkpoint catalog, and common monitor records. If a parent process
was interrupted after training completion, rerunning `train` or entering evaluation reconciles the
same artifact from persisted JSON/catalog evidence without reopening checkpoint models. Existing
ranking evidence must match the re-derived content digest exactly or the campaign fails closed.

ADAPT-RANK1 still does not itself choose campaign finalists. ADAPT-EVAL1 in 0.20.126a0 now
consumes these one-per-run champions for campaign-wide top-K full-fidelity evaluation; historical
EVAL-MF remains readable but is no longer the generated production strategy.

## ADAPT-EVAL1 - top-K authoritative full evaluation and retirement of EVAL-MF screening

**Status:** implemented in `mdstats 0.20.126a0`.

### Retire successive halving from the production path

The production evaluator shall no longer run 10% -> 33% -> 100% mixed-fidelity rounds,
survival fractions, guard-band rescue, or rank-inversion expansion. Historical EVAL-MF
records remain readable, and an exhaustive/reference evaluator may remain available for
diagnostics, but new production campaigns use training monitor evidence for the only
cheap screening stage.

### Campaign finalist queue

Sort the run champions by $S_{\mathrm{light}}$ and initially purchase full evaluation
for

```text
finalist_count = 5
```

champions, or all champions when fewer than five exist. Full evaluation uses the common
full target model-selection/evaluation domain and the common full **true-label** replay
evaluation domain. The model is executed in its own `single|double` dtype; all
mdstats-owned error reductions and statistical calculations are FP64.

The authoritative full force score is

$$
S_{\mathrm{full}}
=
\frac{w_T T_{\mathrm{full}}+w_R R_{\mathrm{full}}}{w_T+w_R}.
$$

Before ranking, reject any candidate with

$$
T_{\mathrm{full}}>T_{\max}
\quad\text{or}\quad
R_{\mathrm{full}}>R_{\max},
$$

or that fails any retained full-evaluation hard gate such as energy, stress, focus-group,
worst-condition, finiteness, or required observable constraints. The weighted score
cannot compensate for a hard failure.

The historical percentage replay-degradation metric against the foundation remains a
reported diagnostic (absolute and fractional degradation) but is no longer the default
hard replay selector. The default replay hard gate is the weight-derived absolute
true-label RMSE ceiling above.

### Finalist rescue

If the first finalist batch contains no fully admissible candidate, evaluate the next
unevaluated champions in batches of

```text
finalist_rescue_batch_size = 5
```

until an admissible candidate appears or the champion pool is exhausted. This bounded
rescue handles lightweight-monitor misranking without restoring EVAL-MF's multi-round
complexity. Once at least one candidate in a purchased batch is admissible, normal
production selection may stop and choose the best fully evaluated admissible candidate
from all purchased batches. An explicit exhaustive mode may evaluate all champions for
research/qualification but is not the production default.

### ADAPT-EVAL1 acceptance gate

The gate closes only when:

1. production evaluation buys no 10%/33% EVAL-MF rounds;
2. the initial full-evaluation purchase is at most five run champions;
3. target and replay full evaluation use common campaign-wide domains and true replay
   labels;
4. `single` candidates infer as FP32 and `double` candidates as FP64, with no cross-dtype
   promotion;
5. metric accumulation and score calculation are FP64;
6. hard target/replay boundaries are applied before weighted ranking;
7. rescue proceeds in deterministic batches only when no purchased candidate is
   admissible; and
8. interrupted full evaluation reuses authenticated completed predictions without
   changing candidate ordering or scientific identity.

### ADAPT-EVAL1 implementation record (`0.20.126a0`)

New generated campaigns use `checkpoint_strategy = "adaptive_topk"` with
`finalist_count = 5` and `finalist_rescue_batch_size = 5`. The production evaluator consumes
only immutable ADAPT-RANK1 champions, orders them by their already-paid lightweight score, and
purchases no EVAL-MF 10%/33% inference. Historical `bounded`, `exhaustive`, and
`multi_fidelity` strategies remain routed through their legacy evaluator for old campaign
evidence.

ADAPT-MON1's 256-frame target monitor remains a training/screening artifact. DATA8 now also
materializes the complete DATA5 outer-monitor domain once as
`shared/target/full_target_evaluation.xyz`; every adaptive bundle must expose the identical
content-addressed artifact. Full replay evaluation uses the complete configured independent TRUE_DFT replay monitor
domain resolved from `[paths].replay_true_labels` and the frozen replay-monitor lineage. Thus neither
lightweight monitor is silently relabeled as authoritative full evidence.

The initial purchased batch contains at most five one-per-run champions. Each candidate is
evaluated on the complete common target and true-replay domains in its own learned-model dtype
(`single` -> FP32 inference, `double` -> FP64 inference). mdstats converts model outputs to FP64
for reductions, retained safety gates, replay-degradation diagnostics, and the weighted full score.
Target and replay absolute RMSE ceilings are enforced before scoring; the historical fractional
replay-degradation threshold is retained only as a reported diagnostic. If no candidate in the
current purchased set is admissible, the next five champions are evaluated. Rescue stops as soon
as at least one fully admissible candidate exists or the champion pool is exhausted.

Naive fine-tuning and multi-head replay now share the same lightweight score geometry. A naive
model still has only its target head and receives no replay gradients, but the fixed 512-frame
TRUE_DFT replay monitor is injected as an auxiliary validation-only loader evaluated through that
target head. It is ordered before the ordinary target loader so MACE 0.3.16's historical
last-validation-loader checkpoint/patience scalar remains target-driven. Multi-head replay keeps its
ordinary `pt_head` monitor. Consequently ADAPT-STOP1/RANK1 scores are comparable across training
methods before EVAL1 performs campaign-wide top-K screening.

Full-evaluation predictions and decisions are content-addressed and restartable. Completed
predictions are reused only when checkpoint identity, policy, common target/replay artifacts, and
model dtype match exactly. ADAPT-EVAL1 records the ordered admissible full candidates but does not
yet perform deployment verification or final fallback/export; that responsibility remains
ADAPT-VERIFY1.

## ADAPT-VERIFY1 - final selection, verification, and precision propagation

**Status:** implemented in `mdstats 0.20.127a0`.

Among all fully evaluated admissible candidates purchased by ADAPT-EVAL1, select

$$
M^*=\arg\min S_{\mathrm{full}}.
$$

The selected checkpoint then enters the existing bounded verification/deployment gates.
Verification does not rerank models unless an existing hard verification failure rejects
the current winner and the policy explicitly permits fallback to the next already fully
evaluated admissible candidate.

The precision boundary remains exact:

```text
single candidate -> FP32 learned-model inference during verification/export
double candidate -> FP64 learned-model inference during verification/export
```

Persistent MD state, accumulated observables, energy-drift regression, and other
mdstats-owned scientific bookkeeping remain FP64. A verification report must state both
the model inference dtype and the invariant analysis/state dtype so users cannot mistake
FP64 bookkeeping for a full-FP64 learned model.

Full-evaluation and verification records shall publish, at minimum:

- common target force RMSE and threshold;
- true replay force RMSE and derived threshold;
- target/replay weights and full score;
- foundation replay RMSE plus absolute/fractional replay degradation as diagnostics;
- retained energy/stress/focus/worst-condition and observable gates;
- model precision and backend identity;
- exact target/replay monitor and full-domain identities; and
- finalist batch/rank provenance.

### ADAPT-VERIFY1 acceptance gate

The gate closes only when final selection, fallback after verification failure, model
export, NVE verification, committee handling, and result summaries all preserve the
binary model dtype and FP64 scientific-analysis boundary, and when no historical
`refine` conversion or EVAL-MF rank can silently determine a new-production winner.

### ADAPT-VERIFY1 implementation record (`0.20.127a0`)

New `adaptive_topk` campaigns route completed authoritative EVAL1 evidence directly into an
ordered deployment-verification path. Fully evaluated admissible candidates are sorted by
`S_full`; the best receives the complete configured structure x temperature bounded-NVE matrix.
If it fails a hard finite/drift/minimum-distance/maximum-force gate and
`fallback_to_next_full_evaluation_candidate = true`, the next already fully evaluated admissible
candidate is tested. No new target/replay evaluation is purchased during fallback, and verification
stops immediately at the first passing candidate. Setting the fallback option false makes failure of
the best full-score candidate terminal.

A candidate may originate from either a fold or a final-development run. The historical committee
export helper therefore cannot define adaptive deployment because it rejects fold-run sources and
would fabricate a different scientific selection. ADAPT-VERIFY1 instead materializes the exact
selected checkpoint, extracts its target head into an internal verification-only artifact in the
learned-model dtype, and runs NVE on those exact bytes. Failed candidate artifacts are not published.
When one candidate passes, those already verified bytes are atomically promoted into `models/`; no
post-verification dtype conversion or fresh export is allowed. Adaptive production publishes one
`AdaptiveDeploymentModelRecord` rather than synthesizing a legacy final-development committee.
Historical committee evidence remains readable and continues to serve historical evaluator paths.

The verification evidence chain is explicit and restartable. Per-case NVE results are content
addressed by checkpoint/model bytes, structure bytes, temperature, timestep, step count, model
inference dtype, acceleration/critical-precision policies, and runtime identity. Candidate-level
`AdaptiveVerificationCandidateRecord` evidence freezes pass/fail reasons and the case digests. A
parent interruption can therefore resume without repeating completed NVE cases. The aggregate
`AdaptiveVerificationRecord` records every attempted fully admissible candidate in score order and
the first passing attempt, if any. `AdaptiveDeploymentModelRecord` binds the published model bytes
to the passing checkpoint and full-evaluation candidate. `AdaptiveProtocolFreezeRecord` binds the
production qualification, common full target/true-replay domains, EVAL1 decision, verification
decision, selected model bytes, learned-model dtype, and invariant FP64 analysis dtype.

Precision semantics remain binary and exact: `single` uses FP32 MACE inference in NVE and publishes
an FP32 learned model; `double` uses FP64 inference and publishes FP64 learned-model bytes. Positions,
velocities/momenta, cell state, energy-drift regression, metric/statistical reductions, and other
mdstats-owned scientific bookkeeping remain FP64 in both cases. The production verification report
publishes the selected candidate's full target/replay RMSE, weighted score, foundation replay
degradation diagnostics, retained energy/stress/focus/worst-condition metrics, exact full-domain
identities, verification thresholds/case results, fallback provenance, acceleration identity, model
dtype, and scientific-analysis dtype.

## ADAPT-MIGRATE1 - schema, restart, storage, and historical compatibility closure

**Status:** implemented in `mdstats 0.20.128a0`.

The final gate closes authority, restart, storage, and historical-compatibility seams after the
new training/evaluation/deployment path has qualified end to end. It deliberately does not change
the scientific policies established by ADAPT-PREC1 through ADAPT-VERIFY1 and does not delete
historical evidence.

### Schema and identity migration

The generated TOML and immutable protocol records shall expose at least:

```toml
[training]
max_num_epochs = 30
online_target_monitor_configurations = 256
online_replay_monitor_configurations = 512
target_stop_fraction = 0.80
replay_stop_multiplier = 1.20

[acceptance]
maximum_target_force_rmse_ev_per_angstrom = 0.030

[evaluation]
target_score_weight = 1.0
replay_score_weight = 1.0
finalist_count = 5
finalist_rescue_batch_size = 5
```

`maximum_replay_force_rmse_ev_per_angstrom` is resolved from the weights and target
threshold by default and may be materialized into resolved-policy evidence. An explicit
user override, if later supported, must be identity-bearing and must not silently change
the weight-derived default semantics.

The policy identity also binds exact monitor memberships, stop multipliers, finalist
count, replay-label lineage, and common full-evaluation domain identities. Changing any
of these invalidates affected training/evaluation selection caches but does not invalidate
upstream source, partition, or feature evidence unnecessarily.

### Historical evidence and restart

- Existing EVAL-MF partial/full records remain readable as historical evaluation
  evidence.
- Existing `single`, `double`, and `refine` precision-profile records remain readable;
  only new `refine` production execution is prohibited.
- Active new-style runs restart from persisted epoch monitor metrics and stop-state
  records exactly; they must not re-decide earlier stop boundaries from newly sampled
  monitors.
- A legacy staged run cannot be resumed under binary semantics without a new scientific
  protocol identity.

### Storage interaction

STOR1-STOR5 ownership boundaries remain valid. Retired EVAL-MF prediction shards and
staged-precision companion state become ordinary historical/reconstructable artifacts;
existing cleanup tiers may reclaim them only under their already-declared lifecycle and
capability-loss rules. The migration gate must not broaden deletion authority or delete
historical evidence merely because the producing algorithm is no longer the default.

### ADAPT-MIGRATE1 implementation record (`0.20.128a0`)

The implemented closure adds a schema-neutral `ProtocolFreezeAuthorityRecord` rather than making
generic lifecycle code guess whether `protocol_freeze` contains a historical committee freeze or
an adaptive deployment freeze. The original scientific freeze remains intact. Historical freezes
are adapted read-only without inventing a model dtype; adaptive freezes bind the learned-model
dtype and invariant FP64 scientific-analysis dtype.

Completed `0.20.127a0` adaptive campaigns are reconciled idempotently: the duplicated adaptive
freeze under the generic `protocol_freeze` alias is replaced only at that alias by the new authority
record, while `adaptive_protocol_freeze`, EVAL1/VERIFY1/deployment evidence, and all historical
EVAL-MF/committee records are preserved. An immutable `AdaptiveMigrationRecord` binds the complete
lineage and records the preserved historical-evidence keys.

Evaluation semantics are now protected by immutable campaign identity. Adaptive STOP1/RANK1
campaigns must use `adaptive_topk`; historical campaigns cannot be reinterpreted as adaptive by
editing TOML, and adaptive campaigns cannot regain EVAL-MF authority the same way. After an adaptive
protocol freeze exists, `evaluate` authenticates/reuses the frozen EVAL1 decision rather than
creating a second post-freeze selection history.

STOR1-STOR5 retain their existing ownership and capability-loss rules, but consequential storage
operations now require a schema-valid protocol-freeze authority rather than mere record-key
presence. STOR1 reporting reads that summary through a read-only SQLite connection, so migration
reporting does not mutate the campaign database.

### End-to-end qualification

Qualification shall include at least:

1. same-data `single` and `double` smoke campaigns proving dtype propagation;
2. monitor-size regressions reproducing the 256-target/512-replay default rationale;
3. synthetic and real learning curves covering target-stop, replay-stop, max-epoch, and
   no-admissible-checkpoint outcomes;
4. weight-ratio tests for 1:1, 2:1, and 1:2 replay ceilings;
5. campaigns where the run champion occurs before the final stopping epoch;
6. top-five full evaluation plus next-five rescue;
7. interruption/restart during training monitor evaluation and during finalist full
   evaluation;
8. historical EVAL-MF/refine report readability; and
9. storage/reporting tests proving obsolete algorithm artifacts remain ownership-safe.

## Completion rule for the adaptive-training revision

This roadmap is complete only when all seven gates are implemented and the production
workflow satisfies all of the following:

1. **binary model precision** - only `single|double` controls learned-model training and
   inference dtype;
2. **FP64 scientific arithmetic** - mdstats-owned fitting, reductions, statistics, and
   persistent simulation bookkeeping remain FP64 without a user-facing mixed mode;
3. **fixed comparable monitors** - 256 target and 512 true-replay defaults provide one
   common lightweight metric basis across competing runs;
4. **criterion-driven training** - target success, replay exhaustion, or the 30-epoch
   ceiling terminates adaptation without assuming monotonic curves;
5. **weight-consistent screening** - the same target/replay weights define the replay
   ceiling, lightweight score, and full score;
6. **hard boundaries precede scores** - neither lightweight nor full weighted averages
   can compensate for target/replay acceptance failure;
7. **one champion per run** - adjacent epochs from one fold cannot monopolize expensive
   evaluation;
8. **full evaluation is sparse** - production initially evaluates only the top five run
   champions and uses bounded batch rescue rather than successive halving;
9. **true replay semantics** - online and full replay error use true labels for the
   absolute threshold, while pseudo labels remain a training mechanism only;
10. **verification preserves model dtype** - FP32/FP64 model identity remains exact
    through final inference and export; and
11. **history remains readable** - retired EVAL-MF/refine evidence is preserved without
    silently controlling new campaigns.

As of `0.20.128a0`, all seven adaptive gates are implemented. New campaigns use the binary
model-precision, common-monitor, adaptive-stop, run-local ranking, top-K full-evaluation, sequential
verification-fallback, and schema-aware migration/storage authority path end to end. Historical
EVAL-MF/refine/committee records remain readable only for the campaigns that created them and do not
silently control new adaptive campaign identities.


# Post-0.20.129 conventional-CV checkpoint-selection and final-model revision

**Status:** architecture recorded in `mdstats 0.20.130a0`; **MLCV-ROLE1 implemented in
`mdstats 0.20.131a0`, MLCV-MON1 in `mdstats 0.20.132a0`, MLCV-STOP1 in
`mdstats 0.20.133a0`, MLCV-RANK1 in `mdstats 0.20.134a0`, MLCV-SELECT1 in
`mdstats 0.20.135a0`, and MLCV-AGG1 in `mdstats 0.20.136a0`**. ROLE1 freezes statistical authority, MON1 materializes role-correct
lightweight/full monitors, STOP1 limits lightweight thresholds to configurable training control,
RANK1 retains run-local top-five candidates, SELECT1 freezes one representative per run from
full role-correct validation, and AGG1 converts only the frozen fold representatives into untouched outer-fold robustness evidence. The remaining MLCV gates own final-seed
production selection, verification, and migration. The gates below intentionally supersede, for new campaigns as they are implemented, the
production selection semantics introduced by
`ADAPT-MON1`, `ADAPT-RANK1`, `ADAPT-EVAL1`, and the fold-winner deployment part of
`ADAPT-VERIFY1`. Historical adaptive evidence remains valid for the campaigns that created it and
must never be silently reinterpreted under this revision.

This revision restores the original DATA5 principle that a cross-validation evaluation fold does
not select its own checkpoint. It also makes the distinction between optimization diagnostics,
checkpoint-selection validation, cross-validation evidence, final-model validation, locked testing,
and physical verification explicit in both data lineage and runtime authority.

## Motivation and correction of the completed adaptive design

The completed post-0.20.120 adaptive revision solved real production problems: it reduced redundant
inference, made stopping criterion-driven, preserved true-replay retention evidence, and made
checkpoint/export lineage restartable. Its implementation is internally consistent with its frozen
specification. The scientific issue is that the specification assigned too many roles to the same
validation domains.

In particular, the completed adaptive path:

1. replaced each fold's DATA5 nested checkpoint monitor with one common target `outer_monitor`;
2. applied the absolute target/replay acceptance thresholds during lightweight ranking;
3. retained only one lightweight champion per run before authoritative full evaluation;
4. pooled fold-run and final-run champions into one campaign-wide finalist queue; and
5. allowed a fold-run champion to become the published production model.

Those choices improve comparability and evaluation cost, but they blur conventional machine-learning
roles. Under this revision:

- **training diagnostics** describe how well the optimizer fits data it is allowed to see;
- **checkpoint-selection validation** controls stopping and selects epochs;
- **cross-validation folds** evaluate the training procedure on data that did not select the epoch;
- **final validation `D`** selects among models trained on the complete development pool;
- **locked test `E`** evaluates the frozen winner exactly once and never selects a fallback; and
- **physical verification** determines whether the statistically selected model is usable as an
  interatomic potential.

The default campaign remains multi-head replay fine-tuning only with three optimizer seeds and three
cross-validation folds plus one full-development final fit per seed:

```text
3 seeds x (3 CV folds + 1 final fit) = 12 training runs
```

Naive/native target-only fine-tuning remains an explicit opt-in comparison protocol, not a default
production campaign member.

## Binding statistical hierarchy

Let the target development pool be conceptually `A + B + C`, let `D` be an independent outer
validation/model-selection domain, and let `E` be a locked post-freeze test domain.

For three-fold cross-validation, the rotating outer folds are:

```text
fold 0: outer CV evaluation = C
fold 1: outer CV evaluation = B
fold 2: outer CV evaluation = A
```

The other two thirds are not used wholesale for gradient training. DATA5 already supports a nested
checkpoint-monitor role inside the training side. Therefore each fold is decomposed as:

```text
fold i:
    gradient-training domain        T_i
    nested checkpoint domain        V_i_full
    lightweight checkpoint subset   V_i_light subset of V_i_full
    outer CV evaluation fold        C_i
```

with hard disjointness:

```text
T_i intersect V_i_full = empty
T_i intersect C_i      = empty
V_i_full intersect C_i = empty
```

`V_i_light` is a deterministic subset of `V_i_full`; it is not an additional statistical role.
The outer CV fold `C_i` is never used for early stopping, lightweight ranking, top-K checkpoint
selection, or tuning of the fold representative.

For each seed's final run:

```text
gradient-training domain        = A + B + C
lightweight target validation   = D_light subset of D_full
full final validation           = D_full
locked post-freeze test         = E
```

`D` is therefore a **validation/model-selection** domain, not a pristine test set. Looking at `D`
to rank epochs or choose among the three final seeds is allowed and is part of its declared role.
`E` remains sealed until the production candidate has been selected and physically verified.

Replay roles remain separate from target CV roles:

```text
replay training domain          R_train      (pseudo labels allowed by policy)
lightweight replay validation   R_light      (TRUE_DFT, default 512 configurations)
full replay validation          R_full       (TRUE_DFT, complete configured validation domain)
```

`R_light` is a deterministic subset of `R_full`. Pseudo labels may affect replay gradients but never
satisfy absolute replay acceptance or final retention evidence.

### Correlation-aware split requirement

Cross-validation is only meaningful if the partition units match the scientific dependence
structure. Frame-wise random shuffling of adjacent AIMD frames is prohibited as the production
default. DATA5 autocorrelation-aware units, trajectory blocks, protected event groups, condition
axes, and profile-defined independence units remain authoritative. The CV split answers the
question encoded by those units; it must not manufacture an easy validation problem by placing
near-duplicate time-adjacent configurations on both sides of a fold boundary.

## Per-epoch metric contract

Every training run shall expose separate diagnostic and validation channels. Names in immutable
evidence must identify the statistical role rather than using an ambiguous generic `target_error`.
At minimum, the runtime shall distinguish:

```text
train_objective_loss
train_target_diagnostic_force_rmse      # optional fixed-size diagnostic inference, default enabled
checkpoint_target_force_rmse            # lightweight target validation
checkpoint_replay_force_rmse            # lightweight TRUE_DFT replay validation
```

The optimizer's accumulated training loss is not interpreted as a post-epoch generalization metric.
Because batches are evaluated while parameters are changing within the epoch, it is retained as an
optimization diagnostic only.

To make over-fitting visible on the same RMSE scale, the generated production policy should also
materialize a deterministic target training-diagnostic monitor from configurations that genuinely
belong to the gradient-training domain. The planned default maximum is 256 configurations. It may
be evaluated with the epoch-final checkpoint and plotted against validation RMSE, but it has **zero
selection authority**: it cannot stop training, rank checkpoints, satisfy acceptance, or rescue a
failed model.

For fold runs:

```text
checkpoint_target_force_rmse  = error on V_i_light
checkpoint_replay_force_rmse  = error on R_light
```

For final runs:

```text
checkpoint_target_force_rmse  = error on D_light
checkpoint_replay_force_rmse  = error on R_light
```

The default lightweight budgets remain:

```text
target checkpoint monitor      256 configurations
replay checkpoint monitor      512 configurations
training diagnostic monitor    256 configurations (diagnostic only)
```

If an eligible parent domain contains fewer configurations than the configured maximum, the
realized monitor size and the resulting statistical limitation must be explicit immutable evidence;
the implementation must not silently duplicate configurations merely to reach the nominal count.

## Threshold semantics: lightweight control versus full acceptance

The existing default full target force-RMSE ceiling remains:

```text
T_max = 0.030 eV/A = 30 meV/A
```

The default replay ceiling remains weight-coupled unless explicitly replaced by a future
identity-bearing policy:

```text
R_max = (w_T / w_R) * T_max
```

so the default 1:1 target/replay score weighting gives:

```text
R_max = 30 meV/A
```

The existing lightweight stopping margins remain useful but acquire a stricter interpretation:

```text
target-success stop level    = f_T * T_max
replay-exhaustion stop level = f_R * R_max

defaults: f_T = 0.80, f_R = 1.20
```

At the default 1:1 weighting:

```text
target-success stop level    = 24 meV/A
replay-exhaustion stop level = 36 meV/A
```

These configurable factors are **training-control heuristics on lightweight validation only**. The generated defaults are 80%/120%; they are not acceptance thresholds and do not certify or disqualify an epoch.

Therefore the new production path must remove the ADAPT-RANK1 rule that requires lightweight
`T <= T_max` and `R <= R_max` before an epoch can be ranked. Any checkpoint with complete finite
lightweight target/replay metrics is rankable. For example, an epoch with a 31 meV/A lightweight
target estimate may still receive full validation and may later prove to satisfy the authoritative
30 meV/A threshold.

Absolute target/replay thresholds become authoritative only when applied to a declared **full
checkpoint-selection validation domain** or to declared outer/final evidence as specified by later
gates.

A configurable minimum evidence floor must prevent an unusually favorable first epoch from ending
training before a meaningful learning trajectory exists. The planned generated default is:

```text
minimum_epochs_before_adaptive_stop = 3
```

The hard maximum epoch ceiling remains 30 by default. The minimum does not force training past a
hard numerical failure or invalid checkpoint.

### Foundation replay feasibility

The completed STOP1 path compares the foundation replay baseline with the absolute replay ceiling
before epoch 0. Under the new distinction between lightweight control and full acceptance, that
feasibility decision must not be based on the 512-frame lightweight estimate alone.

The foundation model shall instead be evaluated once on `R_full`, with reusable content-addressed
prediction/metric evidence. That full TRUE_DFT replay baseline determines whether the requested
retention ceiling is feasible before target adaptation begins. `R_light` remains the per-epoch
forgetting trend monitor.

## Run-local checkpoint-selection hierarchy

Every independent training run owns its own checkpoint-selection problem. Epochs from different
folds, seeds, or final fits never compete until each run has produced one representative.

For a run ending at epoch `N`:

1. compute the lightweight score for every checkpoint with finite monitor metrics;
2. rank checkpoints using the configured target/replay score weights;
3. retain up to five lowest-score checkpoints by default;
4. perform authoritative **run-local checkpoint-selection validation** on those checkpoints;
5. apply hard target/replay acceptance boundaries only at that full-validation stage; and
6. choose the lowest full-score admissible checkpoint as the run representative.

The lightweight score remains:

```text
S_light = (w_T * T_light + w_R * R_light) / (w_T + w_R)
```

and the full checkpoint-selection score remains:

```text
S_full = (w_T * T_full + w_R * R_full) / (w_T + w_R)
```

but scores never compensate for component-wise hard-gate failure. A checkpoint is full-validation
admissible only when both:

```text
T_full <= T_max
R_full <= R_max
```

and all retained energy/stress/focus/worst-condition gates required by the protocol also pass.

`top_k = 5` is a maximum, not an entitlement. If fewer than five checkpoints exist, evaluate the
available set. Deterministic tie-breaking must remain content-addressed and restart-stable. An
optional future diversity rule may impose a minimum epoch separation among purchased checkpoints,
but no such spacing is required by the first implementation.

### Critical nested-CV correction

For **fold runs**, the top-five full target evaluation must use `V_i_full`, not the outer fold `C_i`:

```text
fold checkpoint selection:
    light ranking        -> V_i_light + R_light
    top-five full select -> V_i_full  + R_full
    representative       -> chosen without inspecting C_i
```

Only after the representative is frozen is it evaluated on `C_i`.

This is stricter than selecting the best of five directly on `C_i`. Selecting among five on `C_i`
would make the nominal CV fold part of checkpoint selection and would bias its reported error. The
nested DATA5 monitor exists precisely to avoid that leakage.

For **final runs**, the top-five full target evaluation legitimately uses `D_full` because `D` is
declared as the final-model validation/selection domain:

```text
final checkpoint selection:
    light ranking        -> D_light + R_light
    top-five full select -> D_full  + R_full
    representative       -> best admissible checkpoint on D_full + R_full
```

## Conventional cross-validation evidence

After a fold representative has been chosen without access to `C_i`, mdstats evaluates that exact
checkpoint once on the complete outer fold `C_i`.

The outer-fold target result is the conventional cross-validation estimate for that fold. It must
be recorded separately from the nested checkpoint-selection result. At minimum:

```text
fold_target_outer_rmse
fold_representative_replay_full_rmse
fold_representative_combined_score
```

The combined fold score may combine `C_i` target error with the representative's `R_full` replay
error for deployment-oriented reporting, but the architecture must not pretend that replay has the
same rotating outer-fold independence as the target CV domain. The statistically clean CV target
quantity is the error on `C_i`.

For every seed, all three folds must produce a representative whose outer target error satisfies the
configured target acceptance ceiling. A fold with no full-selection-admissible checkpoint, or a
representative that later fails on its untouched outer fold, marks that seed/protocol CV result as
not robust.

Cross-fold aggregation shall report, separately for target, replay, and combined score where
applicable:

```text
mean
sample standard deviation
minimum
maximum
range
worst fold
```

The first implementation shall make **all-fold survival** a hard CV requirement but shall keep the
magnitude of cross-fold dispersion as a diagnostic/warning rather than inventing an uncalibrated
universal standard-deviation cutoff. A future hard consistency threshold may be introduced only
from empirical campaign evidence and must become an identity-bearing policy.

CV folds are evidence about the **training recipe**. They are not deployment candidates. No fold
checkpoint may enter the final production-model competition merely because it has a lower score than
a full-development model.

## Final-model selection across seeds

Each of the three default seeds produces one final representative trained from the complete target
development pool `A+B+C` and selected using `D_light -> D_full` plus the replay validation domains.
Only those final representatives are eligible for production selection.

Conceptually:

```text
seed 1 final representative --\
seed 2 final representative ---+--> compare on full D + R_full --> best qualified final model
seed 3 final representative ---+
```

The best final representative is determined from full-validation-admissible models by the configured
full target/replay score and deterministic tie-breaking. Fold results may fail the protocol or raise
robustness warnings, but they never directly outrank a final model.

The export layer shall support two explicitly different products:

```text
production_best.model
committee/
    one qualified final representative per seed, when available
```

The production artifact contains exactly one model. The committee contains only qualified **final**
seed representatives and is intended for disagreement estimation and active learning. It must not
contain fold models merely to increase member count.

Exactly three committee members are not guaranteed. If one final seed has no admissible
representative, a three-member qualified committee plus an explicit warning is preferable to
exporting a model that violated the scientific gates. A later policy may launch replacement seeds
when a fixed committee size is required.

### Seed semantics and diversity modes

The generated default remains the statistically paired design:

```text
training seeds vary:       [1, 2, 3]
CV partition seed:         one common fixed value
```

This allows the 3 x 3 CV matrix to separate optimizer stochasticity from partition sensitivity.
The campaign seed controls the MACE stochastic training trajectory; the common fold partition keeps
seed-to-seed CV comparisons paired.

An optional advanced mode may derive a different CV partition from each training seed. Its purpose
must be described as **broader robustness sampling**, not as final-model committee diversification:
all final runs still train on the same `A+B+C`, so changing only the fold partition cannot directly
make the final models more diverse.

The first planned configuration vocabulary is conceptually:

```text
seed_mode = optimizer_only                 # generated default
seed_mode = optimizer_and_cv_partition     # optional robustness mode
```

Any future attempt to deliberately increase final committee diversity through bootstrap/resampled
training domains, architecture perturbations, or other mechanisms requires a separately versioned
scientific policy rather than overloading cross-validation semantics.

Committee diversity shall eventually be measured rather than assumed. A fixed probe set may report
per-configuration force disagreement across qualified final seeds, but disagreement metrics are a
later active-learning/committee qualification stage and are not a prerequisite for this first CV
correction.

## Locked test and physical verification semantics

After final validation chooses the best final-seed representative, bounded physical verification
remains required before production publication. Verification may reject a statistically strong
candidate for physical reasons such as unstable NVE behavior. If verification fallback is retained,
it may proceed only through other already full-validation-qualified **final-seed representatives**;
fold models remain ineligible.

Once one verification-passing production candidate is frozen, the locked test `E` is activated and
evaluated exactly once on that frozen model. `E` is post-selection evidence. If the model performs
poorly on `E`, the campaign fails or requires scientific review/new protocol identity. The program
must not try seed 2, seed 3, or another checkpoint on `E`, because doing so would turn the locked
test into another validation/model-selection set.

The resulting hierarchy is therefore:

```text
training                    -> fit parameters
nested checkpoint monitor   -> stop/rank/select fold checkpoints
outer CV folds              -> judge recipe robustness
D                            -> select full-development checkpoint and seed
physical verification       -> reject statistically good but unusable potentials
E                            -> one-shot post-freeze generalization evidence
production export           -> immutable selected model bytes
```

## Diagnostic artifacts and auditability

Every training run shall generate human-readable and machine-readable diagnostic history under its
run directory. Planned artifacts include:

```text
diagnostics/
    training_history.json
    training_history.csv
    validation_history.png
```

The primary validation plot shall show by epoch:

- lightweight target validation force RMSE;
- lightweight replay validation force RMSE;
- optional target training-diagnostic force RMSE;
- the configured target-success stopping level (default 80% of the full target criterion);
- the full target acceptance threshold as a reference line;
- the full replay acceptance threshold as a reference line;
- the configured replay-exhaustion stopping level (default 120% of the full replay criterion); and
- the realized adaptive stop epoch and stop reason.

The plot legend/caption must state that the 30 meV/A lines are **full-validation acceptance
references, not lightweight rejection gates**. Training-diagnostic RMSE, when present, must be
visually and semantically marked as non-authoritative.

The campaign-level ML diagnostics report shall summarize:

```text
per-run training/validation curves
adaptive stop reasons
run-local top-five lightweight candidates
full checkpoint-selection results
representative checkpoint per run
outer CV target results
cross-fold mean/std/worst/range
seed-to-seed final-validation results
selected production model
qualified committee membership
physical verification result
locked-test result, once activated
```

The report must preserve target and replay components separately even when a weighted combined score
is also shown.

## Ordered implementation sequence

The revision is implemented in the following order. No later gate may silently emulate a missing
earlier gate.

1. `MLCV-ROLE1` - **implemented in 0.20.131a0**: restore and freeze statistical data roles, lineage, and anti-leakage barriers;
2. `MLCV-MON1` - **implemented in 0.20.132a0**: construct fold-local nested/full/light monitors, final `D` monitors, replay monitors,
   training diagnostics, and their persistent history artifacts;
3. `MLCV-STOP1` - **implemented in 0.20.133a0**: convert 80%/120% logic to lightweight control only, add the minimum-epoch floor,
   and move foundation replay feasibility to `R_full`;
4. `MLCV-RANK1` - **implemented in 0.20.134a0**: rank every finite lightweight checkpoint and retain up to five candidates per run
   without lightweight hard-threshold disqualification;
5. `MLCV-SELECT1` - **implemented in 0.20.135a0**: perform run-local top-five full checkpoint selection using `V_i_full + R_full`
   for folds and `D_full + R_full` for final runs;
6. `MLCV-AGG1` - **implemented in 0.20.136a0**: evaluate frozen fold representatives once on untouched outer folds and publish
   conventional CV robustness statistics;
7. `MLCV-FINAL1` - **implemented in 0.20.137a0**: restrict production competition to final-development representatives, choose one
   best final verification candidate, and export the qualified final-seed committee separately;
8. `MLCV-VERIFY1` - **implemented in 0.20.138a0**: restrict physical-verification fallback to qualified final representatives,
   freeze the first physical passer, activate locked `E` only on that frozen model, and publish production only after `E` passes; and
9. `MLCV-MIGRATE1` - **implemented in 0.20.139a0**: close schema/restart/storage/history compatibility, bind the distinct `mlcv_nested_cv` lifecycle authority, and qualify the complete new lifecycle.

### MLCV-ROLE1 acceptance gate

The gate closes only when tests prove that:

1. every fold has disjoint gradient-training, nested checkpoint-selection, and outer-evaluation
   roles;
2. the outer fold cannot be passed to stopping, ranking, or top-five selection APIs;
3. final `D` is explicitly validation/model-selection evidence rather than locked-test evidence;
4. locked `E` remains sealed from training, checkpoint selection, seed selection, and verification
   fallback;
5. replay training labels and TRUE_DFT replay validation lineage cannot be confused; and
6. correlation-aware DATA5 partition units remain the production split authority.

### MLCV-ROLE1 implementation record (`0.20.131a0`)

The first gate is implemented without changing the later adaptive selection behavior. The runtime now:

1. derives an immutable `mdstats.mlcv-role-catalog.v1` from the passing DATA5 partition bundle;
2. records fold-local gradient-training, nested checkpoint-selection, outer-CV-evaluation, and purge unit identities exactly as DATA5 assigned them;
3. reinterprets DATA5 `outer_monitor` as final model-selection validation `D` and preserves `locked_interpolation_test` as locked `E`;
4. records `data5_bundle`, partition-policy, partition-unit-catalog, outer-partition, and CV-plan digests so correlation-aware DATA5 partition units remain the only production split authority;
5. records replay-gradient and replay-validation lineage separately, requires any attached authoritative replay validation artifact to carry `TRUE_DFT` labels, and rejects train/validation geometry overlap;
6. introduces typed role/operation guards that reject outer-CV or locked-test evidence when passed to checkpoint stopping, checkpoint ranking, or top-K checkpoint-selection APIs; and
7. persists `mlcv_role_catalog.json` beside new DATA8 preparation evidence and embeds the same catalog in DATA8 v4 serialization while retaining readers for historical DATA8 v1-v3 payloads.

The generated default campaign is also reduced to three optimizer seeds with three common CV folds plus one final-development fit per seed: `3 x (3 + 1) = 12` multi-head jobs. This seed-count change is an initialization default only and does not reinterpret existing campaign identities.

### MLCV-MON1 acceptance gate

The gate closes only when tests prove that:

1. fold `V_i_light` is deterministic and contained in `V_i_full`;
2. final `D_light` is deterministic and contained in `D_full`;
3. `R_light` is deterministic, TRUE_DFT, and contained in `R_full`;
4. default realized maxima are 256 target-light, 512 replay-light, and 256 target-training diagnostic
   configurations;
5. monitor membership/lineage is immutable and restart-stable; and
6. JSON/CSV/PNG diagnostic artifacts reproduce the persisted epoch metrics without triggering new
   scientific inference during reporting.

### MLCV-MON1 implementation record (`0.20.132a0`)

The second gate changes monitor materialization and per-epoch diagnostics while deliberately preserving
the historical STOP1/RANK1/SELECT behavior for later gates. New DATA8 v5 preparations now:

1. materialize each fold's lightweight target monitor `V_i_light` as a deterministic subset of that fold's DATA5 nested checkpoint-selection domain `V_i_full`; the untouched outer fold `C_i` remains a separate `fold_evaluation.xyz` artifact and is never placed in the MACE validation loader;
2. materialize final-run `D_light` as a deterministic subset of complete final-validation `D_full`;
3. stage complete independent TRUE_DFT replay validation as `R_full` and materialize deterministic `R_light` from it, with default maximum sizes 512 and immutable geometry lineage;
4. materialize a deterministic, selection-inert target-training diagnostic subset from the exact gradient-training membership for every run, with default maximum size 256;
5. use `V_i_light`/`D_light` as the ordinary target MACE validation loader and `R_light` as the replay validation loader, with default target-light maximum 256;
6. inject the target-training diagnostic as an additional validation loader encoded through the target head but logged under `target_train_diagnostic`; it is prepended ahead of ordinary validation loaders so MACE 0.3.16's native last-loader checkpoint/patience scalar remains target-validation-driven and the diagnostic cannot influence optimization, stopping, or checkpoint authority;
7. persist an immutable `mdstats.mlcv-monitor-catalog.v1` binding every run's training, target-light, target-full, training-diagnostic, replay-light, and replay-full memberships to ROLE1 authority; and
8. generate per-run JSON/CSV/PNG diagnostic history from already persisted MACE epoch metrics. Reporting performs zero new scientific inference and shows training objective loss, target-training diagnostic RMSE when available, lightweight target RMSE, lightweight TRUE_DFT replay RMSE, stopping/reference thresholds, and the realized adaptive stop marker.

Historical DATA8 payloads remain readable. MLCV-MON1 intentionally does **not** yet change the old lightweight 30/30 candidate-eligibility rule, the 80%/120% stop semantics, top-K ranking, or production winner hierarchy; those are owned by MLCV-STOP1 and later gates.

### MLCV-STOP1 acceptance gate

The gate closes only when tests prove that:

1. 24 meV/A target success and 36 meV/A replay exhaustion at default 1:1 weighting are lightweight
   stop signals only;
2. a lightweight target/replay value outside 30/30 does not itself disqualify a checkpoint;
3. adaptive stopping cannot trigger before the configured minimum epoch except for hard runtime
   failure;
4. the 30-epoch ceiling remains hard;
5. the foundation replay feasibility gate uses cached `R_full` TRUE_DFT evidence; and
6. restart at a durable stop boundary executes no extra epoch.

### MLCV-STOP1 implementation record (`0.20.133a0`)

The third gate changes only training termination and its evidence authority; run-local top-K ranking
and full checkpoint selection remain owned by later gates. New adaptive-stop policy schema v2 now:

1. treats the configured target-success and replay-exhaustion margins as **lightweight stopping heuristics only**; generated defaults remain 80% and 120%, so with the default 30 meV/A target reference and 1:1 target/replay score weights they resolve to 24 and 36 meV/A respectively; `0.20.135a0` additionally permits valid TOML overrides while preserving the derived relationship to the full criteria;
2. removes the 30 meV/A target and weight-derived replay ceilings from lightweight candidate disqualification. Every checkpoint with complete finite lightweight target/replay RMSE remains rankable; the legacy `candidate_eligible` field is retained temporarily as a compatibility name for lightweight rankability until MLCV-RANK1 replaces the historical record shape;
3. adds `minimum_epochs_before_adaptive_stop = 3` by default. Target-success and replay-exhaustion margins cannot terminate a run before three completed epochs, while `max_num_epochs = 30` remains an independent hard ceiling and may end a shorter explicitly configured budget;
4. evaluates the foundation replay-feasibility baseline once on complete independent **full TRUE_DFT `R_full`** evidence through a temporary validation loader before epoch 0, persists the resulting RMSE plus authenticated replay-artifact SHA-256 in durable stop state, and removes that loader before the epoch loop so no per-epoch full-replay cost is introduced;
5. suppresses the one-shot `R_full` loader on exact restart once the frozen foundation baseline exists, authenticates the bound `R_full` artifact before reuse, and retains the existing durable stop-boundary rule that a restarted MACE child executes no extra training epoch after terminal evidence; and
6. preserves historical ADAPT-STOP1 schema v1 identity and semantics exactly: legacy policy payloads round-trip under their original digest, keep the historical one-epoch margin activation and lightweight 30/30 eligibility behavior, and are never silently upgraded to v2 behavior.

The full 30 meV/A target/replay acceptance gates are therefore no longer authoritative anywhere in
MLCV-STOP1. They are reserved for MLCV-SELECT1, where complete declared full-validation evidence is
actually available.

### MLCV replay-degradation semantic correction (`0.20.140a0`)

A real MLCV preflight exposed one semantic defect in the otherwise-complete nested-CV architecture: the weight-derived replay quantity had been applied as an absolute replay RMSE ceiling. Current authority corrects that meaning without changing data roles or CV geometry.

1. Define `R0_light = RMSE(foundation, R_light)` and `R0_full = RMSE(foundation, R_full)` on exact authenticated domains. These baselines are distinct and may not be substituted across domains.
2. Define signed degradation `DeltaR = R - R0`; negative values are retained as genuine replay improvement.
3. The full replay budget is `DeltaR_max = (w_T/w_R) T_max` unless explicitly overridden. The human-readable absolute ceiling is `R0_full + DeltaR_max`, not `DeltaR_max` itself. For the observed `R0_full = 75.281 meV/A` and default 1:1, 30 meV/A target geometry, the candidate ceiling is `105.281 meV/A`.
4. Foundation evaluation establishes zero degradation and cannot fail because its absolute replay RMSE exceeds the degradation budget. Current MLCV policy schema v3 therefore removes the historical foundation-feasibility escape hatch from generated policy.
5. STOP1 replay exhaustion uses `DeltaR_light >= replay_stop_multiplier*DeltaR_max`; with defaults this is 36 meV/A degradation, equivalent to the matched `R0_light + 36 meV/A` absolute diagnostic line.
6. RANK1 uses `S_light=(w_T*T_light+w_R*DeltaR_light)/(w_T+w_R)` and current deterministic ties prefer score, target, degradation, absolute replay, epoch, SHA.
7. SELECT1 gates `T_full <= T_max` and `DeltaR_full <= DeltaR_max` component-wise, then scores survivors with `S_full=(w_T*T_full+w_R*DeltaR_full)/(w_T+w_R)`.
8. AGG1 and FINAL1 propagate the same degradation-aware combined score while reporting absolute replay RMSE separately. VERIFY1 and locked `E` keep their scientific roles unchanged.
9. Current evidence persists foundation model SHA, exact replay-domain identity, raw replay RMSE, matched foundation RMSE, signed degradation, degradation budget, stop boundary, diagnostic absolute ceiling, weights, and degradation-aware score.
10. Historical v1/v2 absolute-replay evidence round-trips with its original meaning/digest. Transitional STOP1/RANK1/SELECT1/AGG1/FINAL1 derived evidence is stale under current authority. `train` refuses historical MLCV DATA8 stop policies rather than reinterpreting them; lifecycle migration archives the prior authority under its original digest before installing the replay-degradation authority.
11. Deterministic policy/schema/lineage/preflight subprocess failures are non-retryable in one `train` invocation; transient execution failures retain bounded retry.
12. Diagnostics show target-light RMSE, absolute replay-light RMSE, the matched foundation baseline, signed replay degradation, and target/degradation control lines.

This is a semantic migration, not a change to the 3 seeds x (3 folds + 1 final) default geometry, top-five shortlist, fold-freeze/outer-CV separation, final-seed-only production selection, physical verification, or target-only locked `E`.

### MLCV-RANK1 acceptance gate

The gate closes only when tests prove that:

1. every finite checkpoint with complete lightweight target/replay metrics is rankable;
2. no outer fold or full `D` inference is purchased by ranking;
3. up to five candidates are retained independently per run;
4. fewer-than-five trajectories are handled without synthetic duplication; and
5. ranking/tie-breaking is deterministic under restart.

### MLCV-RANK1 implementation record (`0.20.134a0`)

The fourth gate is a zero-new-inference evidence transformation. New lightweight-run ranking schema v2 now:

1. recomputes lightweight rankability from the frozen STOP1-v2 policy and requires complete finite nonnegative target/replay metrics, but applies **no 30 meV/A full-validation rejection**;
2. computes the already-defined lightweight score `S_light = (w_T T_light + w_R R_light)/(w_T+w_R)` independently inside every run and uses deterministic tie-breaking by score, target RMSE, replay RMSE, epoch, then checkpoint SHA-256;
3. retains at most `candidate_limit = 5` checkpoints per run and persists `rankable_checkpoint_count` before truncation so shorter runs remain exact and longer runs are auditable;
4. performs no MACE inference, no model deserialization, no outer-fold inference, and no full-`D` inference; the checkpoint catalog root may be absent and ranking still succeeds from immutable STOP1/catalog evidence;
5. keeps the historical rank-one fields only as a temporary compatibility bridge for ADAPT-EVAL1. They are **not** a fold representative, final representative, or production-selection decision under the MLCV authority; MLCV-SELECT1 will consume all retained candidates; and
6. preserves historical lightweight-run-champion schema v1 as readable authority for campaigns that already own it. Existing v1 evidence is not silently rewritten into v2 top-K semantics.

STOP1 control geometry is explicitly **derived** rather than absolute: `T_stop = f_T*T_full_max`, `R_full_max = (w_T/w_R)*T_full_max`, and `R_stop = f_R*R_full_max`. New campaign TOML defaults remain `f_T = 0.80` and `f_R = 1.20`, but both factors are configurable and become part of the protocol-frozen stop-policy digest. Therefore 24/36 meV/A are only the default 30 meV/A, 1:1 consequences; changing the full criterion, score weights, or configured stop factors changes the lightweight stop margins without changing the authoritative full-validation ceilings.

### MLCV-SELECT1 acceptance gate

The gate closes only when tests prove that:

1. fold top-five target selection uses `V_i_full`, never `C_i`;
2. final top-five target selection uses `D_full`;
3. both use complete `R_full` TRUE_DFT replay evidence;
4. 30 meV/A target and the resolved replay ceiling are component-wise hard gates before scoring;
5. retained energy/stress/focus/worst-condition constraints remain hard gates where configured; and
6. exactly one immutable representative or one explicit no-representative outcome is produced per
   run.

### MLCV-SELECT1 implementation record (`0.20.135a0`)

The fifth gate replaces the historical campaign-wide ADAPT-EVAL1 finalist queue for new MLCV-MON1/RANK1 campaigns with a strictly run-local full-selection contract:

1. every retained RANK1 v2 candidate is evaluated; there is no early batch stop once one survivor appears and no campaign-wide pooling of fold/final checkpoints;
2. a fold run resolves its complete target selection domain from that job's MLCV-MON1 `target_checkpoint_full` artifact, whose authority is `TARGET_CHECKPOINT_SELECTION` (`V_i_full`). The untouched outer fold `C_i` is rejected by ROLE1 and is not queried by SELECT1;
3. a final-development run uses its complete `D_full` `target_checkpoint_full` artifact with `TARGET_FINAL_VALIDATION` authority;
4. all runs use the complete independent TRUE_DFT `R_full` replay artifact, not `R_light`, for authoritative replay acceptance;
5. component-wise hard gates are applied before score ranking: `T_full <= T_full_max` and `R_full <= (w_T/w_R)T_full_max`. Configured target energy, focus-force, stress, and worst-condition limits remain hard gates as well. Replay degradation percentage is not used as a compensating substitute for the absolute full replay ceiling;
6. only surviving candidates receive run-representative ranking by `S_full=(w_T*T_full+w_R*R_full)/(w_T+w_R)`, with deterministic ties by lower target RMSE, lower replay RMSE, original lightweight rank, earlier epoch, then checkpoint SHA-256;
7. exactly one immutable `mdstats.mlcv-run-selection-record.v1` representative or one explicit `no_representative` outcome is produced for each completed run. All retained-candidate evaluations are lineage-bound to the exact full target/replay artifacts and selection-policy digest; and
8. in 0.20.135a0 the `evaluate` command for new MLCV campaigns stopped after SELECT1 and marked the campaign ready for `MLCV-AGG1`; 0.20.136a0 extended the same full-campaign evaluation command through AGG1, and 0.20.137a0 now continues through FINAL1. FINAL1 compares only qualified final-development representatives and exports their target-head committee, but it does not publish a verified production model or activate locked `E`. Historical pre-MLCV monitor campaigns continue to route through their ADAPT-EVAL1 authority.

The STOP1 defaults are also corrected in this release: `target_stop_fraction = 0.80` and `replay_stop_multiplier = 1.20` remain generated defaults but are no longer fixed constants. Valid TOML values (`0 < f_T < 1`, `f_R > 1`) are protocol-frozen and diagnostics render the realized factors rather than hard-coded 80%/120% labels.

### MLCV-AGG1 acceptance gate

**Implemented in 0.20.136a0.** The runtime now binds every fold's SELECT1 representative to one target-only evaluation on the complete immutable `cross_validation_evaluation` artifact. The representative's complete TRUE_DFT `R_full` replay error is reused from SELECT1 rather than re-inferred or rotated. Per-seed summaries use sample standard deviation (`ddof=1` semantics) and preserve target/replay/combined components separately. No production selection is created at this gate.

The gate closes only when tests prove that:

1. each fold representative is evaluated once on its untouched outer fold after checkpoint freeze;
2. no outer-fold result can cause a different epoch from the same fold run to be selected;
3. all-fold survival is a hard robustness requirement;
4. target/replay/combined statistics remain separate and report mean/std/min/max/range/worst fold;
5. cross-fold dispersion is diagnostic by default, with no uncalibrated hard SD threshold; and
6. fold representatives are marked permanently ineligible for production export.

### MLCV-FINAL1 implementation record (`0.20.137a0`)

The seventh gate now enforces final-model semantics rather than allowing fold evidence to re-enter deployment selection. The runtime:

1. treats campaign-level AGG1 `cv_failed` as a recipe-level production block: no final seed and no committee are promoted from a failed configured-CV campaign;
2. authenticates that the per-seed AGG1 records entering FINAL1 are exactly the records embedded in that immutable campaign aggregate, rejecting stale or substituted seed-CV evidence;
3. consumes only `FINAL_DEVELOPMENT` SELECT1 representatives and fails closed if a fold selection is supplied;
4. requires all comparable final seeds to share one SELECT1 policy plus identical `D_full` and TRUE_DFT `R_full` artifact identities;
5. ranks qualified final seeds only by their authoritative full `D_full + R_full` score, then target RMSE, replay RMSE, seed, checkpoint epoch, and SHA-256;
6. identifies exactly one `production_best` verification candidate while explicitly keeping `production_model_published = false` until VERIFY1;
7. exports every qualified final seed, and only qualified final seeds, as target-head committee artifacts bound to checkpoint/selection/export byte identity; failed final seeds are omitted rather than padding committee cardinality;
8. supports explicit zero-fold campaigns as `cv_not_performed` without fabricating CV robustness; and
9. adds `seed_mode = optimizer_only` as the generated default plus optional `optimizer_and_cv_partition`, whose deterministic per-seed fold partitions broaden CV robustness sampling without changing the final-development training domain.

### MLCV-FINAL1 acceptance gate

The gate closes only when tests prove that:

1. only final-development representatives compete for the production model;
2. the default 3-seed campaign can produce up to three qualified final committee members but exactly
   one `production_best` selection;
3. a failed final seed is not exported merely to preserve committee cardinality;
4. default shared folds keep optimizer-seed and partition variance statistically separable;
5. optional per-seed partitioning changes CV robustness evidence without falsely claiming to alter
   final-model training data; and
6. final-seed comparison is restartable and deterministic from immutable full-validation records.

### MLCV-VERIFY1 implementation record (`0.20.138a0`)

MLCV-VERIFY1 now:

1. consumes only qualified MLCV-FINAL1 full-development representatives in deterministic FINAL1 order;
2. permits bounded physical-verification fallback only to the next already-qualified final seed when `fallback_to_next_qualified_final_seed = true`, while fold representatives remain permanently ineligible;
3. freezes the first complete bounded-NVE passer and ends physical fallback before any locked-test data are materialized;
4. activates sealed target test `E` only after that physical freeze, evaluates it target-only on the exact frozen target-head bytes, and records explicit one-shot/no-fallback authority;
5. treats locked-E failure as campaign failure/scientific-review evidence rather than a reason to try another seed/checkpoint;
6. atomically publishes `models/production_best.model` only when the physically frozen candidate also passes locked `E`, with published SHA-256 identical to the qualified FINAL1 committee artifact; and
7. preserves the qualified final-seed committee independently for active-learning disagreement while keeping historical ADAPT-VERIFY1 authority readable.

### MLCV-VERIFY1 acceptance gate

The gate closes only when tests prove that:

1. physical-verification fallback, when enabled, can visit only qualified final-seed representatives;
2. fold checkpoints can never become fallback deployment models;
3. selected model dtype remains exact through verification/export;
4. locked `E` activates only after a production candidate is frozen;
5. `E` is evaluated once and cannot select another seed/checkpoint; and
6. a locked-test failure creates campaign failure/review evidence rather than automatic fallback.

### MLCV-MIGRATE1 acceptance gate

The gate closes only when tests prove that:

1. new campaigns bind a versioned CV/final-selection authority distinct from historical
   `adaptive_topk`;
2. completed ADAPT-MON1/STOP1/RANK1/EVAL1/VERIFY1 records remain readable and ownership-safe;
3. old campaigns are never silently re-ranked under new nested-CV semantics;
4. new campaigns cannot regain fold-winner deployment or lightweight hard-gating behavior by editing
   TOML after protocol identity is frozen;
5. storage retention protects top-five candidates, run representatives, selected final models,
   committee members, locked-test evidence, and diagnostics until their declared lifecycle permits
   reclamation; and
6. end-to-end qualification covers interruption/restart at monitor inference, top-five full
   selection, outer-fold evaluation, final-seed selection, verification, and locked-test activation.

### MLCV-MIGRATE1 implementation record (`0.20.139a0`)

The ninth gate closes the conventional-CV correction without rewriting any earlier scientific evidence. The runtime now:

1. gives new conventional-CV campaigns the immutable evaluator-family identity `mlcv_nested_cv`, recorded in `mdstats.mlcv-lifecycle-authority.v1` together with the campaign digest, ROLE1 catalog digests, MON1 catalog digests, and the run-local top-five limit;
2. treats historical `adaptive_topk` as a different evaluator family. A pre-MLCV adaptive campaign remains bound to ADAPT-STOP1/RANK1/EVAL1/VERIFY1, while a historical bounded/multi-fidelity campaign cannot be redirected into MLCV by editing TOML;
3. recognizes transitional 0.20.131-0.20.138 conventional-CV campaigns by their immutable ROLE1+MON1 DATA8 evidence. Their recorded `adaptive_topk` spelling is accepted only as a transitional alias for `mlcv_nested_cv`; reopening under the canonical spelling does not rerank checkpoints, rebuild folds, or change monitor membership;
4. freezes the complete verified ROLE1->VERIFY1 evidence graph after production publication in `mdstats.mlcv-protocol-freeze.v1`, including all run-local top-five ranking records, SELECT1 run representatives, campaign CV aggregate, FINAL1 selection and committee, VERIFY1 record, locked-E record, published production record, protected checkpoint SHAs, and protected model SHAs;
5. exposes that scientific freeze to schema-neutral storage/restart code as `authority_kind = mlcv_deployment` while retaining the original MLCV freeze intact under `mlcv_protocol_freeze`;
6. writes an immutable `mdstats.mlcv-migration-record.v1` receipt and `results/mlcv-migration.json`. Exact restarts reuse the original freeze timestamp/digest rather than creating a second lifecycle history;
7. migrates already-completed 0.20.138 VERIFY1 campaigns on their first 0.20.139 verify touch by authenticating existing `production_best.model`, physical-verification evidence, and one-shot locked-E evidence. No model inference, outer-fold evaluation, checkpoint selection, or locked-E evaluation is repeated;
8. rejects TOML attempts to redirect a frozen MLCV campaign to `adaptive_topk` unless that spelling is the recorded transitional alias, and always rejects redirection to `bounded`, `exhaustive`, or `multi_fidelity`;
9. keeps STOR2 conservative for MLCV campaigns: top-five checkpoint candidates and frozen representatives remain protected from checkpoint compaction, while generic freeze authority protects the qualified committee and production model bytes. Results/logs/diagnostics remain under their normal retained evidence classes; and
10. preserves historical adaptive, committee, and multi-fidelity evidence read-only. If incompatible historical/adaptive generic freeze authority already claims the same state DB, MLCV migration fails closed rather than creating dual production authority.

MIGRATE1 changes lifecycle ownership and migration semantics only. It does not alter the STOP1 margins, RANK1 order, SELECT1 scores/gates, outer-fold CV measurements, FINAL1 winner, VERIFY1 physical fallback, locked-E decision, or published model bytes.

## Completion rule for the conventional-CV revision

This roadmap is complete only when the production workflow satisfies all of the following:

1. **role separation** - training, checkpoint selection, CV evaluation, final validation, locked test,
   and physical verification are explicit non-interchangeable evidence roles;
2. **no outer-fold checkpoint leakage** - an outer CV fold never stops, ranks, or selects a checkpoint;
3. **diagnostic training error** - training fit is visible but has zero model-selection authority;
4. **lightweight stopping only** - configurable target/replay margins (default 80%/120%) control training but never perform final
   acceptance;
5. **full thresholds are full-validation gates** - 30 meV/A target and the resolved replay ceiling
   are enforced only on declared full validation/evaluation evidence;
6. **top-five is run-local** - each of the 8 planned default runs may purchase up to five full
   checkpoint-selection evaluations before producing one representative;
7. **CV judges the recipe** - three untouched outer folds per seed provide conventional robustness
   evidence and cannot become production models;
8. **final runs produce deployment candidates** - only the two planned full-development seed
   representatives can compete for production or committee export;
9. **paired seeds are the default** - optimizer randomness varies while the CV partition remains
   common, preserving variance attribution;
10. **committee semantics are explicit** - qualified final-seed models may be exported as an
    active-learning committee independently of the one production-best model;
11. **locked testing is one-shot** - `E` cannot become another fallback selector; and
12. **history remains valid** - historical adaptive campaigns remain readable under the authority
    that created them and are never rewritten retrospectively.

Gate authority is now complete. New campaigns use the closed MLCV-ROLE1 through MLCV-MIGRATE1 contracts described above and are bound to `mlcv_nested_cv`; historical campaigns retain the versioned authority that created them. Transitional 0.20.131a0-0.20.139a0 campaigns retain their historical authority; replay-dependent derived evidence is regenerated under 0.20.140a0 rather than silently reinterpreted, while unaffected raw measurements may be reused only with authenticated matching identities. **The nine-gate conventional-CV correction is complete.**



# Post-0.20.162 target-accuracy, foundation-audit, and structural-stability revision

**Status:** staged implementation is active. **TARGET-DATA2A is implemented in `mdstats 0.20.163a0`; FOUNDATION-AUDIT1 is implemented in `mdstats 0.20.164a0`; TARGET-DATA2B is implemented in `mdstats 0.20.165a0`; TARGET-DATA2C in `mdstats 0.20.166a0`; TARGET-DATA2D is implemented in `mdstats 0.20.167a0`; TARGET-DATA2E is implemented in `mdstats 0.20.168a0`; TRAIN2A is implemented in `mdstats 0.20.169a0`; TRAIN2B is implemented in `mdstats 0.20.170a0`; EVAL2 is implemented in `mdstats 0.20.171a0`; DEPLOY-VERIFY1 is implemented in `mdstats 0.20.172a0`; PES-VERIFY1 is implemented in `mdstats 0.20.173a0`; RELAX-VERIFY1 is implemented in `mdstats 0.20.174a0`; DYN-VERIFY2 is implemented in `mdstats 0.20.175a0`; SELECT2 is implemented in `mdstats 0.20.176a0`; and LOCKED-TEST2/final production publication is implemented in `mdstats 0.20.177a0`.** TARGET-DATA2D executes Stage A immediately and freezes executable Stage-B/C evidence contracts and decision logic. TRAIN2B generates the authenticated fixed-budget 10-of-30 and 30-of-30 optimization trajectories; EVAL2 supplies leakage-safe target-first static checkpoint evaluation, TRUE_DFT replay admissibility, uncertainty-aware within-run ranking, and Stage-B target-size evidence. DEPLOY-VERIFY1 proves selected-checkpoint -> target-only export -> ML-IAP/LAMMPS-run-0 numerical parity; PES-VERIFY1 then subjects those exact target-only candidates and the untouched foundation baseline to one common, candidate-independent finite-displacement DFT local-PES probe authority; RELAX-VERIFY1 subsequently requires the PES-qualified target-only candidates to preserve the declared periodic framework/motif graph while reproducing matched zero-K DFT-relaxed geometry; DYN-VERIFY2 subjects RELAX-qualified deployed ML-IAP artifacts to common short finite-temperature NVT->NVE rollouts with persistent structural-damage gates and binds the resulting physical pass/fail evidence back to TARGET-DATA2D Stage C; SELECT2 then freezes the final-development seed order from target-only EVAL2 evidence before physical filtering and selects the first complete DEPLOY/PES/RELAX/DYN passer without replay or rollout-score ranking authority. TARGET-DATA2E materializes only after the authenticated physical Stage-C decision reaches `selected`; LOCKED-TEST2 then consumes only the already frozen SELECT2 candidate and either rejects it or publishes the exact frozen MACE/ML-IAP bytes.
The first-release target-size/training/evaluation/physical-selection/locked-publication sequence is implemented and qualified; AL2 remains a later-generation architecture for campaigns that require new DFT evidence. This roadmap supersedes
for **newly generated campaigns after implementation** the current replay-weighted checkpoint score,
all target/replay performance-driven training termination and validation-driven LR mutation, the historical
target-training-size assumptions, and the three-seed generated default. The existing lightweight monitor defaults (256 target and 512 TRUE_DFT
replay configurations) remain unchanged unless a separate monitor-convergence study explicitly revises
them. Historical campaigns remain bound to the authority and defaults that created them.

## Motivation

The current MLCV workflow can produce a checkpoint with excellent held-out force RMSE while the
resulting interatomic potential relaxes an initially intact framework into a persistently distorted
or topologically broken local minimum. The observed LTA/MPA-0 campaign is a motivating example, not
a generic weighting prescription: zero-shot MPA-0 and a newly fine-tuned candidate both show
framework damage consistent with an incorrect local coordination basin, while an older, more heavily
adapted model is more stable. This is evidence that pointwise interpolation accuracy, foundation-model
retention, and physical local-PES correctness are distinct quantities.

The generic architecture therefore changes the questions asked of the campaign:

1. **Is the target corpus broad enough to cover the relevant physics?**
2. **Does the fine-tuned model improve the foundation model on the target material rather than merely
   remain close to it?**
3. **Does the model reproduce local restoring forces, equilibrium geometry, and topology, not only
   average snapshot forces?**
4. **Is the exact deployed model numerically equivalent to the checkpoint/head that was evaluated?**

The LTA failure may motivate additional generic descriptor classes (bond, angle, coordination, local
tails), but it must not bias the default selector toward Al, aluminosilicates, MPA-0, or any other
material/foundation-specific identity.

## Cross-cutting design rules

### Generic defaults, explicit profiles, explicit campaign overrides

The default selector and trainer are **material-generic and foundation-model-agnostic**. The
architecture distinguishes three levels of configuration:

1. **generic profile (default)** - no element-specific importance assumptions; feature-family budgets
   and species/pair/triplet contributions are normalized so atom count, number of species, or number
   of histogram bins cannot silently determine scientific weight;
2. **material profile** - declares legitimate material semantics such as framework centers, bridge
   species, mobile groups, phases, or chemically meaningful neighbor relationships, without by itself
   implying that one element deserves greater statistical importance; and
3. **campaign override** - explicit, provenance-recorded reweighting justified by campaign-specific
   evidence, for example extra emphasis on a vulnerable local environment discovered during a
   particular active-learning cycle.

Failure analysis may add **generic descriptor families and qualification tests** to the default
protocol. It may not add element-, material-, or foundation-specific default weights. Such weighting
requires an explicit profile/override and becomes part of immutable campaign identity.

### Separate selection weights, training-loss weights, and qualification thresholds

Three independent namespaces are mandatory:

- **coverage/selection weights** control how target configurations are chosen;
- **training-loss weights** control MACE energy/force/stress/replay optimization; and
- **qualification thresholds** control pass/fail decisions for accuracy, replay retention, PES,
  relaxation, topology, deployment parity, and dynamics.

No value may silently flow from one namespace into another. In particular, a descriptor that is
important for coverage does not automatically receive a larger MACE loss weight, and a hard
relaxation threshold does not automatically become an FPS weight.

### Partition before selection

Leakage-safe role assignment precedes diversity selection:

```text
qualified DFT corpus
        |
        v
correlation/lineage groups
(trajectory blocks, source lineage, duplicate families)
        |
        v
train / nested-CV / final-validation / locked-test / challenge roles
        |
        v
physics-stratified diversity selection independently inside each permitted role
```

Highly correlated configurations may not straddle independent evidence roles merely because FPS or
random sampling selected them separately. Frozen challenge/qualification evidence remains outside
training and checkpoint ranking until a deliberately versioned next-generation campaign promotes it.

### Deterministic nested target ladders

Dataset-size experiments use one fixed, material-generic seven-rung ladder with strict nested
membership and immutable digests:

```text
D128 subset D256 subset D512 subset D1024 subset D2048 subset D4096 subset D8192
```

Equivalently, the default cardinalities are `2^7` through `2^13`. The selector emits one deterministic
ranked target ordering and each rung is a prefix of that ordering, so a learning-curve comparison may
not silently change both sample size and the selected physics manifold. If the authorized
training-eligible pool cannot materialize at least three rungs, target-size convergence fails closed
rather than manufacturing duplicate or non-nested samples.

## Revised generated campaign geometry

For development of the new training procedure, the generated default becomes **two optimizer seeds**
with three shared outer CV folds plus one full-development final fit per seed:

```text
2 seeds x (3 CV folds + 1 final fit) = 8 training runs
```

Shared CV partitions remain the default so optimizer-seed variance and fold variance stay separable.
The change is intended to accelerate protocol testing; it does not prevent later `extend-seed`
expansion or a larger seed count for final high-confidence production studies. Historical three-seed
campaigns remain unchanged.

The existing lightweight monitor defaults remain **256 target configurations** and **512 TRUE_DFT
replay configurations**. They are checkpoint-training monitors and are independent of the target
training-corpus size. TARGET-DATA2 determines the production target training size from the separate
`2^7` through `2^13` nested convergence ladder; no ladder cardinality is inferred from the lightweight
monitor sizes.

## Gate FOUNDATION-AUDIT1 - foundation-model target adequacy baseline

**Implementation status (`0.20.164a0`): complete for the static target-side baseline authority.**
FOUNDATION-AUDIT1 is materialized immediately after finalized DATA6 and before replay qualification,
DATA7/DATA8 materialization, preflight, or target training. It reuses the already authenticated DATA6
foundation prediction cache; it does **not** perform a second foundation-model inference sweep. The
immutable `FoundationTargetAudit` binds the exact TARGET-DATA2A development domains, foundation
checkpoint bytes/identity, DATA5/DATA6/model-sweep lineage, metric policy, and structural-provider
identities into the prepare restart receipt. `preflight` and `train` fail closed if this authority is
missing or stale.

For each frozen label domain, the implementation reduces the cached prediction/DFT deltas into global
energy MAE per atom, force-component RMSE, stress-component RMSE when stress labels are present,
species-macro and per-species force RMSE, and exact P90/P95/P99 atomic force-vector error tails
(alongside component-absolute-error quantiles). When DATA6 universal structural evidence is
materialized, the same frozen development frames are also reduced into quantile-conditioned force-error
summaries for generic pair-distance, angular-environment, and smooth-coordination channels. Missing or
degenerate structural channels are not fabricated.

The physical-probe identities required by later PES-VERIFY1 and RELAX-VERIFY1 are frozen now, but their
exact numerical protocols remain intentionally gate-local. Until those gates define and materialize a
matched foundation result, the probe status is `deferred_protocol`, never an invented pass. A later
candidate may not claim matched probe evidence without the corresponding foundation-side evidence under
the same frozen probe identity.

Before target fine-tuning, evaluate the untouched foundation model on the same generic target-side
diagnostics later used for candidates. Persist at minimum:

- global energy, force, and stress errors;
- species-macro force error and per-species force errors;
- P90/P95/P99 force-error tails;
- bond-length-, angle-, and coordination-conditioned error summaries;
- finite-displacement restoring-force probes where available;
- zero-K relaxation geometry and topology outcome; and
- exact foundation-model and target-domain identities.

The audit reports absolute target error and later allows fine-tuned models to report improvement
relative to foundation. It must not contain hard-coded logic such as `if element == Al` or
`if foundation == MPA0`. Initially, the audit may classify campaigns descriptively as
foundation-compatible, moderately mismatched, or strongly mismatched; automatic schedule changes
based on those classes require later empirical qualification rather than an opaque first-release
formula.

**Acceptance:** identical domains/probes are used for foundation and candidate comparison; no target
training occurs before the audit identity is frozen; audit failure cannot be hidden by replay
retention.

## Gate TARGET-DATA2A - lineage-aware, leakage-safe role freeze

**Implementation status (`0.20.163a0`): complete.** DATA5 remains the owner of correlation-aware
partition construction. TARGET-DATA2A adds a first-class immutable `TargetDataRoleFreeze` authority
that authenticates the only units/frames later target-size logic may consume, binds DATA5 outer/CV
digests and leakage evidence, records every authorized development interval, retains source/active-
learning lineage metadata, and fails closed when exact geometry or explicitly authenticated
near-duplicate/correlation families cross independent outer or CV evidence roles. Broad lineage or
generation identifiers are provenance metadata rather than automatically indivisible correlation
families; only explicit correlation-family assertions acquire that fail-closed grouping semantics.
Existing prepared campaigns can derive this compact authority from DATA2/DATA3/DATA5 without
repeating DATA4-DATA9A, and the authority digest is part of the prepare restart receipt.

Strengthen DATA5 role construction so temporal/source correlation is handled before target-size
selection. AIMD trajectories are divided into correlation-aware contiguous blocks or equivalent
authenticated independence units. Duplicate/near-duplicate structural families and active-learning
lineage are tracked explicitly. Independent development, CV/final-evaluation, locked-test, and
challenge roles are assigned at the unit level before any target-size convergence statistic is
computed.

The target-size study may consume only its **training-eligible development domain**. The final
held-out validation, locked-test, challenge, and any other role whose contract forbids hyperparameter
selection are frozen first and excluded from the coverage reference and from any foundation residual
used to select `N_target`. This prevents even apparently harmless structural-distribution information
from an independent evaluation set from leaking into target-size choice.

Within the training-eligible development domain, deterministic coverage must span every authorized
trajectory interval so long trajectories do not contribute only one temporally clustered region.

**Acceptance:** train/evaluation leakage audits remain fail-closed; adjacent highly correlated frames
cannot appear on both sides of an independent role boundary; partition digests are restart-stable;
all evidence used to choose `N_target` is provably drawn only from the authorized size-development
role.

## Gate TARGET-DATA2B - hierarchical physics-stratified local-environment coverage

**Implementation status (`0.20.165a0`): complete for the immutable reference/scoring authority.**
TARGET-DATA2B now materializes one restart-stable `TargetCoverageReference` for every TARGET-DATA2A
size-development domain, binds it to DATA4/DATA5/DATA6 and FOUNDATION-AUDIT1 lineage, and provides the
reference-side subset scorer consumed by later target-size gates. Production DATA6 deliberately stores
species/group-resolved *distributions of atomic local features* as compact frame-level summaries
(mean, width, extrema, and robust quantiles) rather than millions of Python atom objects; TARGET-DATA2B
treats each applicable group/family distribution as a separate hard coverage authority. These are not
generic whole-frame embeddings: local-environment extrema and tails remain explicit coordinates, and
DATA6 structural-event strata separately reserve detected rare local changes. A structural family that
is undefined for a given chemical/domain context is non-applicable rather than fabricated; every
materialized applicable family is evaluated independently against the 95% threshold. Reference weights
are balanced first across DATA5 correlation units and then across valid frames within each unit. Local
leave-one-out radii are computed exactly from those nonuniform weights with a memory-bounded `cKDTree`
neighbor search; no dense `N x N` distance matrix is formed. Robust scalar Q01/Q99 extent channels,
mandatory condition/event strata, and scalar normalized-Wasserstein fidelity diagnostics are frozen
with the same authority. Declared material-profile selection features are consumed only through the
generic profile adapter: each non-constant valid profile scalar becomes its own normalized required
coverage family, while provider-declared environment-class labels become mandatory support strata.
For LTA this preserves mobile-ion/site-class evidence without importing LTA logic into the generic
coverage module. TARGET-DATA2B does **not** create the seven target-size rungs; deterministic ranked
selection and exact nested prefixes remain TARGET-DATA2C.

Replace generic global diversity as the sole authority with **quota first, diversity second**:

1. guarantee coverage of major physics strata;
2. guarantee minimum representation of important local-environment families and tails;
3. apply structural/local-environment FPS within those constraints; and
4. perform global redundancy pruning only after the coverage obligations are satisfied.

### Generic hard/soft coverage axes

Hard or high-priority strata may include, where declared by the data/material profile:

- composition or chemical realization;
- temperature/thermodynamic regime;
- major dataset source (ordinary AIMD, strain, finite displacement, active learning, etc.);
- phase/geometry class; and
- correlation-aware temporal/source blocks.

Soft coverage objectives may include strain regime, local site/environment classes, distortion bins,
force/energy/stress tails, migration-transition environments, and other profile-declared physics.
The implementation must avoid an exponentially large Cartesian quota table; hierarchical quotas and
continuous novelty objectives are preferred.

### First-class generic local-environment coverage descriptors

The generic selector gains the following descriptor families for **every chemically relevant
species/pair/triplet defined by generic neighbor/material semantics**:

1. **bond-length distributions** - fixed histograms or CDF samples plus robust quantiles, widths,
   tails, and local extrema;
2. **bond-angle distributions** - center-resolved and bridge-resolved angular histograms/CDFs,
   quantiles, widths, and extreme distortions;
3. **coordination-number distributions** - hard/hysteretic and smooth coordination statistics,
   including fractions of relevant coordination states and low/high-coordination tails;
4. **local distortion distributions** - species-resolved tetrahedral/polyhedral or generic local
   geometry distortion where such motifs are declared; and
5. **worst-local-environment statistics** - minimum smooth coordination, maximum bond extension,
   maximum local angular distortion, and analogous extrema so one rare unstable site cannot be
   hidden by a normal frame-average distribution.

Generic whole-frame structural embeddings remain useful but cannot replace the species/group-resolved
distributions of atomic local-environment features above. Profiles that economically materialize direct
per-atom environment elements may add them as finer-grained required families under the same
reference-side coverage contract.

### Unbiased hierarchical normalization

Feature influence is normalized hierarchically:

```text
feature family
   -> controlled family budget
species / pair / triplet within family
   -> normalized contribution independent of atom count
histogram / quantile / extrema coordinates
   -> normalized representation independent of feature dimensionality
```

A material containing more oxygen atoms, more species, or more histogram bins therefore does not
receive larger implicit weight. Campaign-specific reweighting (for example, extra emphasis on one
center species) is allowed only through explicit overrides and must be persisted in provenance.

### Rare-event reservation

Frames containing a previously underrepresented coordination state, bond/angle tail, or local
environment extreme receive elevated coverage priority before ordinary FPS redundancy pruning.
The mechanism is generic: the implementation discovers underrepresented species/environment states
rather than naming an LTA/Al failure mode in default code.

### Full-pool reference distributions and zero-shot residual reference

After TARGET-DATA2A freezes independent evidence roles, compute one immutable
`TargetCoverageReference` from the **entire training-eligible target development pool**, not from a
small random proxy. Descriptor construction is expected to be cheap relative to DFT or MACE training,
so all qualified MD/static/strain configurations in that role contribute to the empirical reference
whenever feasible.

The reference contains the physics-stratum frequencies and all normalized structural/local-environment
distributions above. FOUNDATION-AUDIT1 additionally evaluates the untouched foundation model once on
this same training-eligible pool and caches global, species-resolved, and tail residual distributions.
Those residual distributions provide a generic zero-shot representativeness check - whether a nested
subset represents where the current foundation model is weak - but they do not introduce
foundation-specific chemical weights. Foundation results from frozen validation/challenge roles may
be reported separately but have zero authority over `N_target`.

### Reference-side empirical-mass coverage and default threshold

Coverage is pass/fail by **required family**, not by an average that can hide a poorly represented
local environment. The generic default is:

```text
coverage_metric = reference_mass_local_knn
coverage_threshold = 0.95
coverage_resolution_mass = 1 / 128
coverage_leave_one_out = true
```

The word **coverage** has a literal reference-side meaning. It is not range span, mathematical support,
or a renamed distribution-similarity score. For each required descriptor family `f`, the immutable
full-pool reference defines a weighted empirical set

$$
R_f = \{(z_{f,i}, w_{f,i})\}_{i=1}^{N_f},
\qquad w_{f,i} \ge 0,
\qquad \sum_i w_{f,i}=1,
$$

where one `z_{f,i}` is the atomic/local-environment, frame-level, categorical, residual, or other
family element owned by that descriptor family. A frame may induce zero, one, or many family elements;
there is no architectural assumption that every family contains exactly one point per configuration.
The weights are derived from the frozen hierarchical normalization policy so a long trajectory, an
abundant species, or a high-dimensional histogram cannot obtain accidental coverage authority merely
by contributing more raw observations.

A selected target rung `D_N` induces a corresponding representative set `S_f(D_N)`. **The coverage
counter runs over the full reference `R_f`, never over the smaller selected set.** For every reference
element `z_{f,i}`, use the frozen family metric `d_f` and define a leave-one-out local reference scale.
Let

$$
w_{f,j}^{(-i)} = \frac{w_{f,j}}{1-w_{f,i}} \quad (j\ne i)
$$

for non-degenerate references, and let `beta = coverage_resolution_mass`. The local radius is

$$
\rho_{f,i}(\beta)=
\inf\left\{
 r\ge 0:
 \sum_{j\ne i} w_{f,j}^{(-i)}
 \mathbf{1}\!\left[d_f(z_{f,i},z_{f,j})\le r\right]
 \ge \beta
\right\}.
$$

Thus `rho_{f,i}` is the radius needed to contain the frozen fraction `beta` of the *other* reference
mass around that reference element. Leave-one-out construction prevents a point from defining its own
resolution merely through its self-distance or a large self weight. For an equally weighted reference,
this reduces to the distance to the

$$
k_f = \max\!\left(1,\left\lceil \beta (N_f-1)\right\rceil\right)
$$

-th other reference neighbor.

Reference element `z_{f,i}` is covered by rung `D_N` iff

$$
\min_{s\in S_f(D_N)} d_f(z_{f,i},s) \le \rho_{f,i}(\beta).
$$

The family coverage score is therefore

$$
C_{\beta,f}(D_N\mid R_f)
 =
 \sum_i w_{f,i}
 \mathbf{1}\!\left[
   \min_{s\in S_f(D_N)}d_f(z_{f,i},s)
   \le \rho_{f,i}(\beta)
 \right].
$$

The required generic criterion is

$$
C_{\beta,f}(D_N\mid R_f) \ge 0.95
\qquad\text{for every required family }f.
$$

Consequently, `C = 0.95` means exactly that at least 95% of the normalized empirical reference mass
has a selected representative within its frozen local reference neighborhood. Two extrema cannot game
this criterion: they may span the full scalar range, but interior reference mass remains uncovered.
Likewise, a subset that is internally homogeneous but occupies only the center of the reference domain
fails because reference elements outside that region have no sufficiently local representative.

The default `beta = 1/128` is tied to the smallest admissible target-size rung and defines one common
reference-mass resolution for the entire `128 ... 8192` study. It is **not** changed to `1/N` for each
rung. The resolved `beta`, family metrics, weights, reference descriptors, and all local radii are
frozen before any rung is scored and are part of size-study identity. A profile may explicitly
override `beta`, but may not tune it after inspecting which rung passes.

Because the ladder is exactly nested and the reference metrics/radii are fixed,

$$
D_{128}\subset D_{256}\subset\cdots\subset D_{8192}
\quad\Longrightarrow\quad
C_{\beta,f}(D_{128})\le C_{\beta,f}(D_{256})\le\cdots\le C_{\beta,f}(D_{8192}).
$$

Coverage is therefore mathematically non-decreasing as configurations are added. A measured reversal
is an implementation, identity, or numerical-consistency defect and fails the coverage audit; it is not
interpreted as physical evidence that a larger nested subset covers less of the same reference.

### Separate extent/range guard

Local empirical-mass coverage also penalizes a subset that does not reach the populated reference
domain, but the global 95% rule intentionally permits up to 5% of reference mass to remain uncovered.
For physically interpretable scalar channels where tail/range preservation matters, the coverage
profile therefore freezes a separate robust extent guard. For scalar channel `x`, define

$$
I_{f,x}^{\mathrm{ref}}
 =
 [Q_{\alpha}(R_{f,x}),\,Q_{1-\alpha}(R_{f,x})],
$$

The generated material-generic default is `alpha = 0.01`, using weighted reference quantiles under the
same frozen hierarchical weights as the corresponding coverage family. With no profile-specific tolerance,
a selected rung passes the scalar extent guard only when

$$
\min S_{f,x} \le Q_{0.01}(R_{f,x})
\qquad\text{and}\qquad
\max S_{f,x} \ge Q_{0.99}(R_{f,x}).
$$

Equivalently, the selected set must place at least one representative in both the lower and upper 1%
reference tails of every declared scalar extent channel. The generated default has **no numerical extent
tolerance**: channel-specific tolerances may be introduced only by an explicit material profile/campaign
override with units, rationale, and immutable provenance. Raw minimum/maximum may be used only when source
semantics establish that extrema are trustworthy. Neither `alpha` nor a tolerance may be inferred or tuned
after inspecting which rung passes.

This extent test is deliberately separate from local coverage. A two-point extrema subset can pass the
extent guard while failing empirical-mass coverage; a dense center-only subset can fail the extent
guard even if it is homogeneous within its own occupied region. Physically meaningful scalar ranges
such as bond lengths, forces, strain/distortion coordinates, coordination measures, or declared tail
observables are appropriate for this guard. Arbitrary coordinate-wise min/max tests are not imposed on
high-dimensional learned embeddings unless a profile gives those coordinates physical meaning.

### Required strata and rare/disconnected regimes

The global 95% mass criterion is not allowed to erase rare but mandatory physics. Required
profile-declared strata retain explicit support-presence rules, and rare-event reservation remains
binding. This is particularly important when a physically distinct stratum carries less reference mass
than `beta`: an unrestricted k-neighbor radius could otherwise cross a large inter-regime gap in order
to accumulate its required local mass.

For a mandatory rare/disconnected stratum `c`, the policy may additionally define a conditional
reference `R_{f|c}` and require stratum-local empirical-mass coverage

$$
C_{\beta,f,c}(D_N\mid R_{f|c}) \ge \tau_{f,c},
$$

or an explicit minimum-presence rule, with the stratum threshold frozen in the coverage profile. Thus
99% coverage of ordinary AIMD environments can never compensate for zero representation of a required
composition, temperature/source class, coordination state, migration-transition family, strain class,
or other declared rare regime.

### Distribution fidelity is a distinct diagnostic

First-Wasserstein, total-variation, histogram/CDF, and analogous distribution discrepancies remain
useful, but they answer a different question: whether already represented regions occur in the selected
set in approximately the same proportions as in the reference. They are therefore recorded as
**distribution-fidelity diagnostics**, not mapped to `C_f = 1 - d_f` and not described as "95%
coverage".

For continuous scalar/distribution families the diagnostic may retain a robustly normalized
first-Wasserstein distance; categorical/discrete families may retain total-variation distance; learned
embedding families may report an appropriate frozen distribution discrepancy in addition to their
reference-mass coverage. A profile may declare a separate fidelity threshold when scientifically
justified, but that threshold has its own name and provenance and cannot substitute for the
reference-side 95% coverage gate.

A block/bootstrap estimate respecting trajectory correlation may accompany borderline coverage or
fidelity results as uncertainty evidence, but the frozen nominal reference, metric, local-resolution
mass, weights, extent policy, and thresholds retain deterministic decision authority.
**Acceptance:** coverage reports prove reference-side empirical-mass representation against the full
authorized training-eligible reference; the coverage counter is demonstrably reference-side; every
required family independently reaches the frozen 95% threshold under one fixed `beta`, metric, weight,
and leave-one-out radius policy; nested-rung coverage is non-decreasing by construction; declared
scalar extent guards and mandatory-stratum/rare-event rules pass independently; Wasserstein/TV results
are labeled distribution-fidelity diagnostics rather than coverage; family-wise normalization tests
show invariance to atom-count/species-count duplication; generic runs import no LTA-specific weighting
logic; zero-shot residual evidence is role-scoped and cannot leak held-out evaluation data into
target-size selection.

## Gate TARGET-DATA2C - deterministic seven-rung target-size ladder

**Implementation status (`0.20.166a0`): complete for deterministic ladder construction and rung evidence.**
TARGET-DATA2C consumes only the frozen TARGET-DATA2A role authority and TARGET-DATA2B coverage
reference. It does not decide which rung advances to training; Stage-A elimination remains
TARGET-DATA2D. For every label domain, the implementation builds one immutable ranked order up to
the largest materializable rung, scores every materialized prefix against the same TARGET-DATA2B
reference, records unavailable larger rungs explicitly, and audits nested coverage monotonicity.

Selection is **quota first, diversity second**. Required TARGET-DATA2B condition/event/profile
strata and every TARGET-DATA2A correlation-aware development interval become explicit reservation
obligations. A deterministic greedy reservation first chooses frames that satisfy the largest number
of still-unmet obligations, breaking ties by novelty in the selector metric and then by stable frame
UID. Each materialized rung therefore carries both its ordinary TARGET-DATA2B coverage report and a
separate mandatory-obligation pass/fail record; a rung cannot later be called Stage-A qualified merely
because its continuous coverage is high while some authorized trajectory interval is absent.

After quota reservation, the remaining order is filled by exact deterministic maximin FPS in one
hierarchically normalized fused feature space assembled from **all required TARGET-DATA2B families**.
Within each family, coordinates are scaled by the frozen TARGET-DATA2B robust scales and normalized
for dimensionality; individual families receive equal budget inside their semantic family; semantic
families receive equal top-level squared-distance budget. If a family is applicable to only part of
the domain, absent frames are center-imputed for the geometric coordinates and carry an explicit
presence coordinate, so absence is represented without fabricating an extreme local geometry. No
random seed is required by the current selector; deterministic tie tolerance and ranking algorithm
identity are frozen in `TargetDataLadderPolicy`.

The campaign prepare receipt now contains the immutable `TargetDataLadderPlan`. `preflight` and
`train` authenticate it before continuing, so a changed role freeze, coverage reference, ladder
policy, or rung identity requires preparation to be regenerated rather than silently reusing stale
size-study evidence.

Materialize the fixed generic ladder:

```text
2^7   = 128
2^8   = 256
2^9   = 512
2^10  = 1024
2^11  = 2048
2^12  = 4096
2^13  = 8192 configurations
```

The selector creates one deterministic ranked configuration ordering under TARGET-DATA2B and defines
each rung as a prefix, guaranteeing exact nesting:

```text
D128 subset D256 subset D512 subset D1024 subset D2048 subset D4096 subset D8192
```

Every selector input, feature definition, normalization policy, coverage profile, deterministic seed
(if any), ranked ordering, and rung membership receives an immutable digest. A descriptor/binning/
normalization/profile change invalidates the old size study instead of silently regenerating a
nominally identical `D2048`.

The default ladder is bounded at 8192 for predictable campaign cost. A material whose available
training-eligible pool cannot materialize at least three distinct rungs fails the generic size-study
precondition. Extending beyond 8192 is an explicit later decision, not an automatic hidden expansion.

The lightweight checkpoint monitors remain separate artifacts with their existing defaults of 256
target and 512 TRUE_DFT replay configurations; they are not ladder rungs merely because a cardinality
matches.

**Acceptance:** exact nestedness and deterministic restart are tested; membership changes only when
selector policy/input identity changes; all seven rungs are attempted when the pool supports them and
unavailable rungs are reported explicitly rather than fabricated.

## Gate TARGET-DATA2D - hard coverage plus 3/10/30 successive-fidelity target-size convergence

**Corrected implementation status (`0.20.182a0`): complete for decision authority, campaign dispatch, exact continuation evidence, and downstream provenance.**

TARGET-DATA2D now separates **support coverage** from **training sufficiency**. Coverage is a hard
admissibility gate only. Every coverage-qualified target size is retained for a common low-fidelity
training screen; size reduction is driven by target learning evidence at 3, 10, and 30 epochs.

The corrected funnel is

$$
7 \xrightarrow{\mathrm{hard\ coverage}} N_{\mathrm{eligible}}
  \xrightarrow{3\ \mathrm{epochs}} \le 4
  \xrightarrow{10\ \mathrm{epochs}} 2
  \xrightarrow{30\ \mathrm{epochs}} 1.
$$

The staged resource-allocation pattern is related to successive-halving methods [30,31], but mdstats
retains project-specific deterministic metrics, hard gates, exact continuation, and provenance. The
full normative correction is frozen in
`docs/specs/training_data/mlff_size_halve1_target_size_revision_spec.md`.

The generated policy surface is:

```toml
[target_data.size_convergence]
ladder_exponents = [7, 8, 9, 10, 11, 12, 13]
minimum_materializable_rungs = 3
reserve_required_strata = true
reserve_correlation_intervals = true
fps_tie_tolerance = 1.0e-12
coverage_metric = "reference_mass_local_knn"
coverage_threshold = 0.95
coverage_resolution_mass = 0.0078125
coverage_leave_one_out = true
extent_quantile_alpha = 0.01
extent_default_tolerance = "none"
min_coverage_qualifiers = 3
coarse_training_epochs = 3
max_coarse_training_candidates = 4
coarse_target_monitor_configurations = 256
short_training_epochs = 10
max_short_training_candidates = 2
final_training_epochs = 30
coarse_practical_equivalence_mev_per_a = 1.0
practical_equivalence_mev_per_a = 1.0
screening_optimizer_seed = 1
```

All fields that can change a scientific decision are versioned authority. The coarse practical-
equivalence width is independently configurable; omission inherits the final width.

### Stage A - hard coverage admission: retain every qualified rung

For every materializable rung, evaluate the frozen TARGET-DATA2B reference-side empirical-mass
coverage, scalar extent, and mandatory-support predicates. With multiple target label domains, a common
rung qualifies only if every domain passes. Distribution-fidelity diagnostics remain diagnostic and do
not gain hard-coverage authority.

Stage A performs no economic size ranking:

```text
if number_qualifying < 3:
    raise TargetDataCoverageError
else:
    retain every qualifying rung
```

This corrects the former rule that retained the four smallest coverage-qualified rungs. A small subset
can span the required range and local-environment support while sampling that support too sparsely for
accurate learning. Larger coverage-qualified sizes therefore remain scientifically relevant until the
training response demonstrates otherwise.

TARGET-DATA2C v3 supports this contract by materializing every globally materializable configured rung.
Historical v1/v2 plans remain archival regression evidence but are stale as current generated-campaign
authority.

### Stage B0 - coarse training: all qualified rungs to at most four at epoch 3

Every hard-coverage-qualified candidate starts once from the same frozen foundation checkpoint, screening
optimizer seed, and nominal **30-epoch** TRAIN2 schedule. The run pauses after exactly three completed
epochs; it is not a three-epoch-normalized schedule.

At epoch 3, EVAL2 evaluates only a common target-side role. The generated default caps this role at 256
configurations. It is deterministically balanced across development correlation blocks, sampled from the
same leakage-safe development complement used by the full target-size role, and shared identically by
every candidate size. Replay inference is not purchased and has no ranking or gating authority in this
coarse round.

The primary ranking quantity is the unrounded target-only force selection score
$S_{\mathrm{target}}^{(3)}$. If more than four candidates remain numerically valid, retain at most four.
If three or four coverage-qualified candidates exist, all numerically valid candidates may continue.

The coarse endpoint must be strictly past LR warm-up. Generated campaign preflight enforces

$$
\frac{E_{\mathrm{coarse}}}{E_{\mathrm{final}}}
> p_{\mathrm{warmup,end}}.
$$

The default gives $3/30=0.10>0.05$.

### Stage B1 - short training: epoch-3 survivors to two at epoch 10

Epoch-3 survivors resume from their authenticated boundary states and continue to exactly ten completed
epochs on the original 30-epoch schedule. The same common full target-size role is used for candidate
comparison. TRUE_DFT replay may be persisted diagnostically at epoch 10 but contributes zero ranking
credit and cannot reject a numerically valid candidate.

Evidence records completed/planned epochs, optimizer updates, structures presented, normalized schedule
progress, instantaneous LR, wall time, target score, checkpoint identity, optimizer/scheduler identity,
RNG identity, foundation identity, training-policy identity, schedule identity, and evaluation-role
identity.

### Early-stage practical equivalence preserves the ladder boundary

The old smaller-size preference is unsafe during epoch-3/10 elimination: it can remove the largest tested
boundary while scores are still practically tied, making later bounded-ladder nonconvergence impossible
to observe.

At epochs 3 and 10, candidates are partitioned by the applicable practical-equivalence width. The largest
hard-coverage-qualified boundary candidate is moved to the front **within its own equivalence band**. It
receives no protection against a materially better earlier band. Thus the boundary survives a practical
tie when capacity permits, but can still be eliminated when materially worse.

At epoch 30, the economic smaller-size preference is restored within final practical equivalence.

### Stage C - full qualification: two finalists to one at epoch 30

The two epoch-10 finalists resume from exact saved state and complete the same 30-epoch trajectory. Neither
target nor replay monitor crossings may terminate a normal finalist early. Final selection combines target
metrics with hard replay retention and the required physical qualification evidence. A smaller set wins a
final practical tie only when the applicable physical and retention evidence is also acceptable.

If the largest available rung remains materially better than its smaller finalist, the result is
`nonconverged_at_ladder_boundary`; the workflow requests target-pool or ladder expansion rather than
silently declaring the bounded maximum converged.

### Exact continuation identity

Promotion changes only the execution pause limit. The authenticated chain is

$$
(\theta_0,o_0,r_0)
\rightarrow(\theta_3,o_3,r_3)
\rightarrow(\theta_{10},o_{10},r_{10})
\rightarrow(\theta_{30},o_{30},r_{30}),
$$

where $\theta$ is checkpoint/model state, $o$ is optimizer/scheduler state, and $r$ is Python/NumPy/Torch
CPU/CUDA RNG state. Epoch-10 evidence must authenticate the epoch-3 parent checkpoint, optimizer, and RNG
identities; epoch-30 evidence must authenticate the epoch-10 parents. Restart may not renormalize the
schedule or recreate a scientifically different run.

### Separation from the production CV/seed campaign

The 3/10/30 size funnel is a procedure-development experiment. After one `N_target` is selected, the
ordinary production campaign runs at that fixed size using the generated default

```text
2 optimizer seeds x (3 shared outer CV folds + 1 final-development fit) = 8 runs
```

The production-corpus authority records every coverage-qualified rung, all epoch-3 evidence, the at-most-
four epoch-3 survivors, all epoch-10 evidence, the two finalists, final evidence, and the selected size or
explicit nonconvergence/failure outcome.


## Gate TARGET-DATA2E - production target-corpus decision and provenance

**Corrected implementation status (`0.20.182a0`): complete for immutable 3/10/30 production-corpus decision/provenance authority.** The gate is deliberately pure and fail-closed: it does not run Stage-B0/B1/C training and cannot create a provisional winner. While TARGET-DATA2D is awaiting epoch-3, epoch-10, or epoch-30 evidence, no TARGET-DATA2E production-corpus record is valid. A completed `failed` or `nonconverged_at_ladder_boundary` outcome cannot be converted into a production target-size claim. Only an authenticated TARGET-DATA2D `selected` outcome may materialize TARGET-DATA2E.

The v2 materialized authority freezes the exact winning frame membership separately for every target label domain and authenticates that membership as an exact prefix of the TARGET-DATA2C v3 master order. It also freezes the TARGET-DATA2A role/partition lineage, FOUNDATION-AUDIT1 domain identity, TARGET-DATA2B coverage policy/family-reference digests, every hard-coverage-qualified Stage-A rung, all epoch-3 evidence and survivors, all epoch-10 evidence and finalists, final evidence, and the selected-size decision. The selected rung's complete TARGET-DATA2B coverage report remains embedded so reference-mass coverage, extent results, mandatory-stratum results, and distribution-fidelity diagnostics remain auditable without rerunning the selector. Foundation-residual reference families are separately indexed inside the same authority.

Campaign integration is intentionally downstream-safe. `_ensure_target_production_corpus_decision()` returns no provisional authority while TARGET-DATA2D is waiting, deletes any stale premature record, fails closed for completed non-convergence/failure, and persists/reuses the decision only after selection. Because an ordinary `prepare` can legitimately finish before TRAIN2/EVAL2/VERIFY generate Stage-B0/B1/C evidence, TARGET-DATA2E is not inserted into the current prepare-restart receipt; later gates must call and authenticate it before launching the fixed-size production CV/seed campaign.

The winning target size is the **smallest qualified nested corpus that is not meaningfully worse than
a larger alternative under the staged evidence above**. A larger subset is justified only when it
improves `S_target` by more than 1 meV/A or materially improves a still-nonconverged required physical
metric. Printed/rounded report values never control the decision.

The decision report records, at minimum:

- frozen training-eligible coverage-reference digest;
- frozen independent-role/partition digests;
- ranked-order and all rung membership digests;
- per-family reference-mass coverage scores, frozen `beta`, metric/weight identities, and local-radius policy;
- scalar extent-guard and mandatory/conditional rare-stratum coverage results;
- separate Wasserstein/TV or other distribution-fidelity diagnostics where configured;
- foundation-residual representativeness summaries;
- Stage-B0 3-epoch target-only metrics, update counts, structures presented, and coarse-survivor decision;
- Stage-B1 10-epoch target metrics, update counts, structures presented, and replay diagnostics (explicitly non-ranking evidence at this stage);
- Stage-C 30-epoch target/PES/relaxation/dynamics/replay evidence;
- every early boundary-preserving equivalence decision and final smaller-size practical-equivalence decision; and
- whether the bounded ladder genuinely converged or terminated at its maximum.

If convergence is not demonstrated within the bounded ladder, the workflow fails closed for a claim
of target-size convergence. Additional highly correlated MD frames are not assumed to solve missing
physics coverage; the correct remedy may be new DFT configurations, a revised target pool, or an
explicitly extended ladder.

**Acceptance:** `N_target` is reproducible from frozen evidence; replay has no positive ranking role;
all target-size decisions are auditable independently of the later two-seed production campaign.

## Gate TRAIN2A - replay becomes a hard retention constraint, not a selection reward

Remove replay degradation completely from checkpoint and final-seed ranking for the new policy.
Replay remains independently evaluated on authenticated TRUE_DFT replay evidence and remains a hard
pass/fail retention gate:

```text
candidate admissible iff replay_degradation <= allowed_degradation
```

Among replay-admissible candidates, replay improvement or extra unused replay margin earns **zero
selection-score credit**. Target-side quality alone ranks survivors, subject to all other hard safety
and physical gates.

The retention ceiling is a **checkpoint/full-evidence admissibility rule, not a training-stop rule**.
An intermediate lightweight replay monitor may temporarily exceed the eventual full replay ceiling and
later recover; under TRAIN2B this does not terminate the run or mutate its LR schedule. Only genuine
numerical/operational invalidity (for example non-finite loss/model state or an unrecoverable training
failure) may abort a normal training trajectory before its planned budget.

This deliberately turns replay into a guardrail against catastrophic general-domain forgetting
rather than a competing destination that can reward insufficient adaptation toward a foundation
model whose target-material PES may itself be wrong.

**Acceptance:** score/tie-break schemas contain no replay term after admissibility; historical
replay-weighted policies retain their original meaning/digests; migration never silently reranks old
campaigns.

### TRAIN2A implementation record (`0.20.169a0`)

TRAIN2A is implemented as policy, protocol-identity, materialization, and migration authority. Newly
generated campaign TOMLs explicitly select `policy_generation = "train2"` and
`checkpoint_strategy = "train2_target_first"`. They freeze four orthogonal v1 policy records:
`TrainingBudgetPolicy`, `LearningRateSchedulePolicy`, `CheckpointAdmissibilityPolicy`, and
`CheckpointSelectionPolicy`. The corresponding `TrainingProtocolIdentity` and production-materialization
plan use new v6 schemas only when the complete TRAIN2 policy family is present. Historical adaptive-stop
protocols/materialization plans retain their v5 serialization/digest behavior and are not translated.

`CheckpointAdmissibilityPolicy` owns the absolute target threshold plus the foundation-relative TRUE_DFT
replay-degradation ceiling. `CheckpointSelectionPolicy` exposes only target observables: replay values are
not accepted by its ranking API, are not serialized as weights, and cannot resolve a tie after
admissibility. Stable candidate identity is the deterministic final exact tie-break after target evidence
and checkpoint maturity. New-policy configuration fails closed if it also supplies historical
performance-stop or replay-weighted selection controls. Absence of `policy_generation` remains an
explicit backward-compatibility signal for historical adaptive-stop campaign files.

TRAIN2A originally stopped at policy authority; TRAIN2B now owns execution for new-policy `train`.
The historical adaptive trainer is still never relabeled as TRAIN2: the wrapper activates a distinct
fixed-budget/per-update runtime only when a complete TRAIN2 protocol is present. EVAL2 now owns the
new-policy `evaluate` path and cannot fall through to historical MLCV/ADAPT selectors. `verify` remains
fail-closed for TRAIN2 until DEPLOY/PES/RELAX/DYN and SELECT2 own the physical qualification path.
Historical campaigns continue to execute under their original policy family.

### Versioned TRAIN2/EVAL2 policy authority and migration

The existing `AdaptiveTrainingStopPolicy` is a historical authority whose fields intentionally entangle
stop margins, replay-weighted scoring, epoch budget, monitor/head names, and adaptive scheduler behavior.
It remains readable with exactly its historical semantics, but it is **not mutated into the new policy**.
New TRAIN2/EVAL2 campaigns instead freeze four orthogonal, versioned policy records:

- `TrainingBudgetPolicy` - planned epoch/update budget, checkpoint cadence, and genuine-failure termination
  authority;
- `LearningRateSchedulePolicy` - base LR identity, exact progress-normalized multiplier function, phase
  boundaries, and per-update scheduler state;
- `CheckpointAdmissibilityPolicy` - target hard thresholds, foundation-relative TRUE_DFT replay ceiling,
  and later physical/deployment pass/fail requirements; and
- `CheckpointSelectionPolicy` - target-only primary observable, shortlist purchase rule, practical/statistical
  equivalence policy, deterministic secondary target ordering, maturity preference, and a stable replay-independent exact tie-break.

Their schema versions and digests become part of run/campaign identity. New-policy configuration may not
silently accept historical adaptive-stop controls such as `target_stop_fraction`, `replay_stop_multiplier`,
patience/plateau termination, or validation-driven scheduler mutation. Supplying mutually inconsistent
historical and TRAIN2/EVAL2 policy keys fails closed with an explicit migration/configuration error.
Historical campaigns are never silently translated, rerun, or reranked; they continue to deserialize under
the authority that created them. A deliberate new-generation migration creates new TRAIN2/EVAL2 identities
rather than reinterpreting old evidence in place.

## Gate TRAIN2B - fixed-budget adaptation plus deterministic low-learning-rate refinement

Retire **all target/replay performance-driven early stopping** for newly generated TRAIN2 campaigns,
including CV runs, target-size screening/continuation runs, and full-development final fits. A normal run
completes its prescribed optimizer budget. The current generated full-trajectory default remains 30
epochs; a future budget change is permitted only as an explicit, identity-bearing protocol revision.
Target and TRUE_DFT replay monitors remain visible throughout training, but they are diagnostics: they
cannot terminate a numerically valid run and cannot trigger LR reduction, scheduler mutation, or
checkpoint acceptance.

The only legitimate pre-budget termination is a genuine training failure such as non-finite objective,
non-finite model/optimizer state, corrupt restart state, or unrecoverable runtime failure. A target RMSE
becoming "good enough" or a replay RMSE temporarily becoming "too high" is not a failure.

### Progress-normalized deterministic LR schedule

The LR policy is defined by the zero-based optimizer-update index rather than noisy validation behavior.
For a frozen planned total of `U >= 2` optimizer updates, the multiplier used **for optimizer update `u`** is
computed from

$$
p_u = \frac{u}{U-1}, \qquad u=0,1,\ldots,U-1,
$$

and the generated default multiplier is the exact piecewise function

$$
m(p)=
\begin{cases}
0.10 + 0.90\,\dfrac{p}{0.05},
& 0 \le p < 0.05,\\[8pt]
0.10 + \dfrac{0.90}{2}
\left[1+\cos\left(\pi\dfrac{p-0.05}{0.75}\right)\right],
& 0.05 \le p < 0.80,\\[10pt]
0.01 + \dfrac{0.09}{2}
\left[1+\cos\left(\pi\dfrac{p-0.80}{0.20}\right)\right],
& 0.80 \le p \le 1.
\end{cases}
$$

Thus

$$
\mathrm{LR}_u = \mathrm{LR}_0\,m(p_u),
$$

which gives the exact phase geometry

```text
0.00 <= p < 0.05    warm-up:              0.10 * LR0 -> 1.00 * LR0
0.05 <= p < 0.80    target adaptation:    1.00 * LR0 -> 0.10 * LR0 (cosine)
0.80 <= p <= 1.00   local-PES refinement: 0.10 * LR0 -> 0.01 * LR0 (cosine)
```

The scheduler advances exactly once per optimizer update, not once per epoch, batch-group, validation event,
or checkpoint. The update index, planned `U`, and scheduler state are persisted so a restart computes the same
next `p_u` and LR as an uninterrupted run. A generated TRAIN2 run with fewer than two planned optimizer updates
is invalid rather than receiving an ad hoc schedule.

`LR0` is the already configured base fine-tuning LR; the architecture freezes **relative multipliers
and phase fractions**, not a new universal absolute LR. The default 5%/75%/20% geometry and LR scales
are configurable only through an explicit protocol-frozen override. Any MACE/native adaptive scheduler that
would also mutate LR is disabled or bypassed for TRAIN2 so two schedulers can never compete.
`ReduceLROnPlateau`, validation-triggered scheduler changes, target/replay threshold-triggered LR changes,
and patience-based termination are prohibited under this policy because they make seed/fold/target-size
trajectories respond to monitor noise rather than to one comparable optimization protocol.

The mandatory final 20% low-LR phase is not optional cleanup. It is part of the scientific training
recipe and exists to refine the target PES after coarse foundation-to-target adaptation. Replay remains
present in the training objective according to the frozen multi-head recipe and remains continuously
monitored, but its hard retention ceiling is applied during checkpoint qualification rather than used
to stop optimization mid-trajectory.

### Successive-fidelity continuation semantics

For the TARGET-DATA2D 3 -> 10 -> 30 epoch funnel, every size-study run is initialized with the **30-epoch
schedule horizon from the beginning**. Epoch 3 and epoch 10 are durable screening checkpoints on that one
trajectory, not endpoints of separately normalized short schedules. A surviving rung resumes without
changing planned-update count, phase boundaries, LR history, or data/optimizer identity.

The runtime continuation companion authenticates model/checkpoint state, optimizer/scheduler state, and
Python/NumPy/Torch CPU/CUDA RNG state. Epoch-10 evidence must prove ancestry from the exact epoch-3
boundary; epoch-30 evidence must prove ancestry from the exact epoch-10 boundary. This prevents a nominal
restart from silently becoming a new training experiment.

### Training-history evidence

Persist for every epoch/checkpoint at minimum:

- completed and planned optimizer updates;
- normalized progress `p`;
- phase identity (`warmup`, `adaptation`, `refinement`);
- instantaneous LR and base LR;
- training objective/loss components;
- lightweight target diagnostics;
- lightweight TRUE_DFT replay diagnostics; and
- any numerical-failure reason.

**Acceptance:** a numerically valid new-policy run cannot terminate because target or replay performance
crosses a threshold; validation cannot alter LR; the final refinement phase is always reached for a
completed run; epoch-3 survivors and epoch-10 finalists resume on the same 30-epoch schedule trajectory; and
restart preserves model/checkpoint, optimizer/scheduler, RNG, progress, LR, and phase identity.

### TRAIN2B implementation record (`0.20.170a0`)

TRAIN2B implements the executable new-policy training path without changing historical adaptive campaigns.
The mdstats MACE wrapper source-qualifies the MACE 0.3.16 training loop, disables the native validation
scheduler as an LR authority, neutralizes patience as a performance stop, and sets the frozen TRAIN2 LR
immediately before **every** `optimizer.step()`. The runtime obtains `U` from the actual training-loader
length times the frozen 30-epoch budget; every optimizer parameter group must begin at the protocol-frozen
`LR0`, and a completed run therefore reaches the exact `p=1` refinement endpoint.

TARGET-DATA2D now uses **successful durable pauses at 3-of-30 and 10-of-30**. The runtime plan retains the
full 30-epoch budget and full planned-update/structure horizon from initialization. Promotion may change
only the execution pause limit: 3 -> 10 -> 30. Scientific restart identity requires unchanged training
protocol, optimizer policy, budget/LR policy, update geometry, and structures-presented geometry. A
latest-only TRAIN2 continuation companion binds the exact raw MACE checkpoint and restores live non-EMA
parameters, EMA state, Python/NumPy/Torch CPU/CUDA RNG states, and base-LR identities before the next
update. The raw checkpoint carries optimizer state; its SHA256 plus protocol/optimizer/update identity
forms the authenticated optimizer-state reference. Restart never renormalizes the remaining horizon into
a new LR schedule.

Each durable epoch writes `train2_runtime.json` plus an append-only TRAIN2 history. The evidence records
completed/planned epochs, optimizer updates, and structures presented; normalized schedule progress; phase;
instantaneous/base LR authority; raw checkpoint and optimizer-state identities; available training loss;
and validation force diagnostics. For replay-enabled TRAIN2 runs the parent supplies the DATA8-authenticated
TRUE_DFT `R_light` artifact and its SHA256. The patched MACE validation loop injects it under the distinct
`train2_true_replay` diagnostic identity using the replay head. It is visible at every validation epoch but
never creates adaptive-stop state, scheduler mutation, checkpoint ranking credit, or a termination signal.
Changed/missing TRUE_DFT monitor bytes fail closed. TRAIN2B v1 also fails closed if a retired staged `refine`/`mixed` precision runtime is present: the executable policy requires one fixed FP32 or FP64 precision stage, so precision-stage checkpoint hooks cannot compete with the TRAIN2 continuation authority.

Campaign execution is target-size-stage aware. While TARGET-DATA2D awaits Stage B0, the screening seed's
final-development job for **every hard-coverage-qualified size** runs to epoch 3. EVAL2 then retains at
most four candidates. Those survivors reopen with `--restart_latest` and continue to epoch 10; EVAL2 keeps
two finalists, which reopen again and continue to epoch 30. After target-size selection, only the selected
size's production matrix is required for completion: two seeds times three CV folds plus one final fit.
Eliminated-size jobs do not block the selected production matrix.

Focused qualification perturbs continuation identities and proves that both the 3->10 and 10->30
boundaries fail closed when checkpoint, optimizer, RNG, schedule, or policy ancestry changes. The coarse
endpoint is also required to lie strictly past LR warm-up; with current defaults, $3/30=0.10$ exceeds the
0.05 warm-up endpoint. A changed LR authority is rejected, worsening validation cannot trip patience, and
a modified TRUE_DFT replay-monitor file is rejected before stages that authorize replay diagnostics.

## Gate EVAL2 - target-first checkpoint-trajectory evaluation and uncertainty-aware ranking

**Implementation status (`0.20.171a0`): complete for static target/replay checkpoint evaluation and uncertainty-aware within-run selection.** EVAL2 has its own immutable `Eval2TargetRole`, `Eval2EvaluationPlan`, checkpoint/metric/bootstrap records, and `Eval2RunRecord`; historical `CheckpointEvaluationRecord` inference/cache machinery is reused only as the byte-authenticated prediction substrate, not as the ranking authority. New-policy `evaluate` dispatches directly to EVAL2 and cannot fall through to replay-weighted MLCV/ADAPT selectors.

Role correctness is explicit. CV runs rank checkpoints only on their frozen DATA5/TARGET-DATA2A internal checkpoint-monitor units. Final-development target-size runs may **not** reuse the historical outer-monitor artifact. EVAL2 freezes one common development-only complement equal to the authorized TARGET-DATA2A development pool minus the largest hard-coverage-qualified training rung. Because TARGET-DATA2C rungs are nested, this complement is disjoint from every candidate rung and is common to the epoch-10 and epoch-30 size stages. Its frame order, source artifact digests, role digest, and correlation-block IDs are authenticated and cached.

For epoch 3, EVAL2 derives a second `size_development_coarse` role from that same complement. The generated policy caps it at 256 configurations, balances quotas across development correlation blocks, and chooses deterministic systematic interior positions. Every size receives the exact same coarse role. The role size is scientific policy and therefore enters TARGET-DATA2D identity rather than remaining an execution-only knob.

At TARGET-DATA2D Stage B0, EVAL2 purchases exactly one **target-only** epoch-3 endpoint evaluation for every hard-coverage-qualified size; no replay inference, rescue search, bootstrap checkpoint ranking, or physical verification is executed. At Stage B1 it purchases the exact epoch-10 endpoint for the at-most-four survivors; TRUE_DFT replay may be persisted there but remains diagnostic-only and has zero ranking credit. At 30 epochs, EVAL2 uses the authenticated full trajectory and existing target/replay evaluation machinery, including admissibility and rescue logic where applicable. Physical qualification remains a separate VERIFY authority: an EVAL2 final record alone cannot finalize `N_target`.

Training completion and model selection are separate authorities. Every finite persisted checkpoint
remains part of the learning trajectory; lightweight target/replay inference during training records
that trajectory but does not stop optimization or certify a model.

### Target-side evidence

Global force RMSE remains the default primary target-selection observable but loses exclusive scientific
authority. Candidate reports include:

- global target force RMSE;
- per-species force RMSE;
- species-macro force RMSE so abundant species cannot hide a weak minority environment;
- P90/P95/P99 and worst-condition force errors;
- framework/mobile-group or other profile-declared strata where meaningful;
- energy/atom and relative-energy metrics; and
- stress metrics where labels exist.

The generated relative-energy diagnostic is offset-insensitive and composition-safe: within each exact atomic-composition group containing at least two configurations, EVAL2 centers the signed per-atom energy error by that group mean and reports the pooled centered RMSE. Singleton composition groups are non-applicable rather than being assigned an invented zero.

The primary checkpoint score `S_target` is target-only and is frozen before training. The generated
default is full target force RMSE; an alternative target-only primary metric requires an explicit
profile/protocol override. Replay never contributes a positive or negative ranking term after its hard
admissibility check, and arbitrary weighted mixtures of global RMSE, tails, species metrics, and replay
are not introduced merely to manufacture one scalar.

### Deterministic target-first full-evaluation shortlist

After the full training budget completes, build the initial expensive full-evaluation shortlist from
lightweight **target** evidence only. The generated default purchases at most five initial candidates:

```text
3 best finite checkpoints by lightweight S_target over the full trajectory
+ 2 best finite checkpoints from the refinement phase (p >= 0.80)
= at most 5 unique checkpoints
```

Duplicates are removed deterministically and vacancies are backfilled in target-rank order while
preserving at least one refinement-phase candidate whenever one exists. This prevents a transient
mid-training validation minimum from excluding every mature low-LR checkpoint. Lightweight replay is
reported but does not rank the shortlist and does not apply the authoritative replay ceiling.

Each shortlisted checkpoint receives full target evaluation and authenticated full TRUE_DFT replay
evaluation. Full target thresholds and the foundation-relative replay-retention ceiling are the first
scientific eligibility gates. If the initial shortlist contains no admissible checkpoint but additional
finite checkpoints remain, deterministic bounded rescue may evaluate the next target-ranked checkpoints;
rescue order is still target-only and its configured cap is identity-bearing. Exhausting the cap without
an admissible model is an explicit run failure, not permission to reintroduce replay-weighted scoring.

### Practical and statistical indistinguishability

Checkpoint comparisons use unrounded full target evidence. The generated practical-equivalence scale is

```text
checkpoint_practical_equivalence_mev_per_a = 1.0
```

A target-score difference of `<= 1.0 meV/A` is practically indistinguishable. For differences larger
than that scale, a paired block bootstrap over the frozen trajectory/source correlation units estimates
uncertainty in the target-score difference. The generated bootstrap policy is:

```text
bootstrap_replicates = 2000
bootstrap_confidence = 0.95
bootstrap_interval = "percentile"
bootstrap_min_independent_blocks = 10
bootstrap_seed = deterministic hash/evaluation-plan digest derivation
```

Each replicate resamples the **same frozen correlation blocks with replacement for both candidates** and
recomputes the target-score difference using the original within-block observations and frozen target
weights; candidate predictions are never resampled independently. A checkpoint is called **materially
better** only when its target improvement exceeds the practical-equivalence scale and the paired 95%
percentile interval excludes zero in the favorable direction. With fewer than 10 independent blocks, the
bootstrap has no decision authority: the workflow records insufficient independent-block support and
falls back to the deterministic 1 meV/A practical-equivalence rule rather than fabricating precision.
Bootstrap seed derivation, block identities, replicate count, interval method, and confidence level are
persisted as evaluation-plan evidence.

Within one run, target-eligible/replay-admissible checkpoints are ordered lexicographically:

1. materially better full `S_target`;
2. if target performance is practically/statistically indistinguishable, lower maximum force RMSE over
   the applicable frozen target strata/conditions (`max_c RMSE_c`);
3. if still indistinguishable, lower species-macro force RMSE;
4. if still indistinguishable, lower target force-error P95;
5. if still indistinguishable, lower target force-error P99;
6. if still indistinguishable, prefer the **later/lower-LR refinement checkpoint**;
7. if still exactly tied, use the frozen stable candidate identity as the deterministic final tie-break.

A secondary diagnostic that is not applicable to the frozen target/profile is skipped, never replaced by
zero or an invented value. Profile-declared hard stratum/tail ceilings are applied as eligibility gates
before this ordering and therefore cannot be traded against another diagnostic. Replay has already spent
all of its authority at the admissibility gate: unused replay margin cannot separate otherwise tied
qualified candidates.

Hard species/tail ceilings may be introduced only after calibration on representative generic materials;
until then they are recorded diagnostics plus profile-specific gates. The 1 meV/A checkpoint-maturity
rule is distinct from TARGET-DATA2D's 1 meV/A **dataset-size** equivalence rule: within a run, a tie favors
mature low-LR refinement; across target-size rungs, an otherwise qualified tie favors smaller `N_target`.

**Acceptance:** metrics are role-correct, deterministic, and weighted independently of raw atom counts;
full-evaluation purchase includes mature refinement candidates; no validation statistic can stop or
reschedule training; replay has no composite-score authority; paired uncertainty uses the frozen 2000-
replicate/95%-percentile/10-block minimum policy and deterministic seed derivation; secondary target ties
follow the frozen worst-stratum -> species-macro -> P95 -> P99 ordering; and an outer/locked domain used for
final reporting cannot leak into training or checkpoint ranking.

## Gate DEPLOY-VERIFY1 - prove target-head/export/deployment numerical parity

**Implementation status (`0.20.172a0`): complete.** TRAIN2 `verify` now resolves only final-development EVAL2 winners: the two screening-seed target-size finalists while TARGET-DATA2D awaits Stage C, or the selected-size final-development production seeds after `N_target` is frozen. Cross-validation-fold models remain evidence-only and are never converted into deployment candidates.

Deployment equivalence becomes a prerequisite to expensive physical qualification. On a frozen probe
set, compare:

```text
selected multi-head checkpoint, explicit target head
        ~ exported target-only MACE model
        ~ deployment artifact / ML-IAP LAMMPS run 0
```

Energy, forces, and stress (where supported) must agree within dtype/deployment tolerance. Exact model
bytes, head identity, export transform, dtype, and probe-set digest are persisted. A mismatch is an
export/deployment failure, not a training/PES failure.

The generated probe cohort contains at most 16 configurations and is selected deterministically from the exact EVAL2 target role by correlation-block round-robin: one representative per independent trajectory/source block is purchased before a second representative is taken from any block. The record binds the EVAL2 target-role digest, target-artifact digest/bytes, ordered frame UIDs, block IDs, and configuration indices.

The executable implementation performs two independent comparisons. First, the exact selected raw checkpoint is reconstructed through the authenticated DATA8 configuration; its explicit `target_head` predictions are compared with an atomically exported single-head MACE model. Second, that target-only model is converted through MACE's ML-IAP exporter and evaluated by the configured LAMMPS executable with `pair_style mliap unified ... 0` and `run 0` on every frozen probe. LAMMPS energy/forces and periodic-cell stress are compared back to the Python target-only MACE prediction. Float32 defaults use `rtol=1e-5, atol=1e-6`; float64 defaults use `rtol=1e-9, atol=1e-10`; all values are configurable but identity-bearing.

The deployment receipt freezes selected checkpoint bytes/epoch, reconstructed-model bytes, exported target-only bytes, ML-IAP bytes and export transform digest, target head, dtype/tolerance policy, probe identity, LAMMPS executable path **and SHA-256**, launch arguments, and run-0 prediction digest. Reuse is allowed only when all of those identities still authenticate. A different LAMMPS build, model/export bytes, EVAL2 winner, probe role, or parity policy forces a fresh deployment verification. Absence or failure of a working ML-IAP LAMMPS runtime fails closed; Python-only export equality is not treated as proof of deployed equivalence.

**Acceptance:** physical relaxation or MD is never interpreted scientifically until the deployed
artifact has demonstrated equivalence to the selected candidate. DEPLOY-VERIFY1 completion leaves the overall `verify` stage waiting for PES-VERIFY1 rather than falsely marking physical verification complete.

## Gate PES-VERIFY1 - generic finite-displacement restoring-force probes

**Implementation status (`0.20.173a0`): complete.** PES-VERIFY1 is the first scientific physical-accuracy gate after DEPLOY-VERIFY1. It does not reuse static validation RMSE as a proxy for local stability. Instead it freezes one candidate-independent finite-displacement request, obtains matched fixed-geometry DFT single-point labels on exactly those geometries, and compares the untouched foundation model and every surviving target-only deployment candidate against the same local-PES evidence.

### Candidate-independent base structures and modes

The base cohort is inherited from the authenticated DEPLOY-VERIFY1 correlation-block-round-robin target probe authority, rather than selected from model errors. The first-release default uses at most four correlation-balanced base configurations, purchasing one representative per independent block before a repeated block whenever the DEPLOY cohort permits it. Because the DEPLOY membership is frozen before PES predictions exist, neither a successful nor a failed candidate can cause a favorable finite-displacement point to be purchased.

For each base, the generic structural generator discovers up to four semantically distinct local modes. Campaign profiles may prioritize generic atom groups/motifs through the material-profile interface, but the PES core contains no LTA-, Al-O-, zeolite-, or composition-specific branch. The default mode vocabulary is:

- shortest chemically allowed neighbor-pair **bond stretch/compression**;
- exact geometric-gradient **bond-angle bending**;
- local **coordination-shell breathing/displacement**, with profile focus groups eligible for priority;
- one small periodic **strain** mode when a periodic cell is available, rotating among hydrostatic, orthorhombic, and shear variants across bases.

The default atomistic displacement magnitude is

$$
|q| = 0.04\ \text{\AA},
$$

where the full Cartesian displacement direction is normalized to unit Frobenius norm. The default strain amplitude is

$$
|q_{\varepsilon}| = 0.01.
$$

Every mode is evaluated symmetrically at `-q` and `+q`, and each base geometry `q=0` is also included once. Thus four bases with four modes require at most 36 DFT single points. These amplitudes, neighbor-cutoff scale, base count, mode count, strain enablement, and all numerical acceptance tolerances are configurable but are part of the immutable PES policy identity.

### Fixed-geometry DFT request and restart contract

`verify` writes a common `results/pes-verify1/probe-request.extxyz`, a probe manifest, and one VASP `POSCAR` directory per requested point. The campaign then returns `WAITING` rather than inferring physical qualification from the MLFF. Auto-collection occurs only when every probe directory contains `INCAR`, `KPOINTS`, `POTCAR`, and `vasprun.xml`. The collector requires identical `INCAR`, `KPOINTS`, and `POTCAR` bytes across all probe calculations; POTCAR contents are never copied into the campaign record, only their SHA-256 identity is retained. Any ionic/cell relaxation that changes the requested geometry beyond the default `1e-6 A` geometry tolerance is rejected.

An externally generated labeled ExtXYZ can be supplied instead, but the caller must provide an explicit DFT protocol digest. Reference membership, ordered probe UIDs, requested geometry, reference bytes, DFT protocol identity, and available source-file hashes are all frozen. A rerun reuses a completed reference only when these identities still authenticate; otherwise the gate returns to the request state or fails closed.

### Centered local-PES comparison

Thermal/AIMD target bases need not be exact stationary points. Therefore the force test uses **centered increments relative to the matched DFT/model `q=0` prediction**, rather than assuming zero base force. For an atomistic normalized mode direction $\hat u$, define the projected force

$$
f(q)=\mathbf F(q)\cdot \hat u
$$

and centered side increments

$$
\Delta f_{\pm}=f(\pm q)-f(0).
$$

The model must reproduce both side increments within a mixed absolute/relative tolerance and, whenever the DFT increment is resolved above the noise floor, it must reproduce the DFT restoring-force direction. A sign reversal is a hard mode failure even if a global force RMSE is small.

The symmetric force-derived stiffness is

$$
k_F=-\frac{f(+q)-f(-q)}{2q},
$$

while the energy curvature is

$$
k_E=\frac{E(+q)+E(-q)-2E(0)}{q^2}.
$$

Both magnitude and resolved curvature sign are checked independently. Strain modes use the analogous centered stress projection/slope plus energy curvature per atom; strain qualification therefore requires DFT and model stress on the common probe set.

First-release default tolerances are deliberately explicit and identity-bearing:

| quantity | absolute tolerance | relative tolerance |
|---|---:|---:|
| centered projected force | `0.05 eV/A` | `0.25` |
| force-derived stiffness | `0.50 eV/A^2` | `0.30` |
| atomistic energy curvature | `0.50 eV/A^2` | `0.30` |
| strain stress projection/slope | `0.01 eV/A^3` | `0.30` |
| strain energy curvature | `1.0 eV/atom` | `0.30` |

Restoring-force sign is considered resolved above `0.02 eV/A`; stiffness sign above `0.25 eV/A^2`; strain-stress sign above `0.002 eV/A^3`. PES-VERIFY1 v1 is an **all-generated-modes hard gate**: partial-mode success is not a supported interpretation.

### Foundation baseline and candidate authority

The untouched FOUNDATION-AUDIT1 checkpoint is evaluated on the exact same DFT probes and frozen as a matched baseline. Its pass/fail result is diagnostic: a fine-tuned target model is not required to outperform the foundation on every mode merely to be admissible. Each deployment candidate, however, must pass the absolute DFT PES criteria. Failed candidates remain immutable evidence and cannot proceed to RELAX-VERIFY1; if every deployment candidate fails, the verification stage fails.

The PES campaign receipt binds the DEPLOY-VERIFY1 campaign/run identities, target-only model bytes, FOUNDATION-AUDIT1/checkpoint identity, policy, common probe/request/reference identities, foundation prediction/qualification digest, and every candidate prediction/qualification digest. A completed result is reusable only while all of those identities and model/reference bytes still authenticate.

**Acceptance:** the probe suite detects wrong restoring-force direction and wrong local curvature even when snapshot RMSE is favorable; finite-displacement membership is frozen independently of checkpoint ranking; all candidates see exactly the same DFT geometries; reference calculations are fixed-geometry and protocol-authenticated; all generated modes must pass; and PES completion leaves `verify` waiting for RELAX-VERIFY1 rather than granting production authority.

## Gate RELAX-VERIFY1 - zero-K topology preservation plus quantitative geometry fidelity

**Implementation status (`0.20.174a0`): complete.** RELAX-VERIFY1 consumes only candidates that already passed PES-VERIFY1 and evaluates them on one common, candidate-independent zero-K relaxation authority. The relaxation bases are inherited from the frozen PES-VERIFY1 base cohort, so a successful or failed candidate cannot change which structures are purchased for DFT relaxation. The first-release default retains at most four correlation-balanced bases.

### Matched fixed-cell DFT relaxation authority

`verify` writes `results/relax-verify1/relax-request.extxyz`, a manifest, and one frozen `POSCAR` directory per common base, then returns `WAITING`. Every DFT reference calculation must use identical `INCAR`, `KPOINTS`, and `POTCAR` bytes. The original request `POSCAR` bytes are authenticated before collection so the reference cannot silently start from a different geometry. RELAX-VERIFY1 v1 is intentionally a **fixed-cell ionic relaxation** protocol; the final cell/PBC/atom identity must remain equal to the request within the configured geometry tolerance.

The default DFT convergence ceiling is

$$
\max_i |\mathbf F_i| \le 0.03\ \mathrm{eV}/\text{\AA}.
$$

A DFT relaxation that reaches the end of its ionic budget without satisfying that force ceiling is not admissible reference evidence. More importantly, the DFT-relaxed reference must itself preserve the declared protected topology relative to the initial requested base. If DFT breaks that graph, the reference is rejected rather than allowing a similarly broken MLFF relaxation to count as accurate.

An externally supplied DFT-relaxed ExtXYZ is supported only together with an explicit protocol digest. Reference bytes, protocol identity, base membership, ordered frame UIDs, preserved-group membership, and convergence forces are immutable evidence.

### MLFF zero-K relaxation protocol

Every PES-qualified target-only deployment candidate is relaxed from exactly the same starting bases. RELAX-VERIFY1 v1 freezes ASE `FIRE` with

- fixed cell;
- force convergence `0.03 eV/A`;
- at most `500` optimizer steps; and
- the deployed model dtype/device already authorized by the campaign.

Performance or validation statistics cannot shorten this relaxation. Non-finite energy/forces, optimizer failure, exceeding the force ceiling after the step budget, or changed model bytes fail the candidate. The per-base optimizer step count, final maximum force, and relaxation energy change per atom are recorded; the energy change is a diagnostic in v1 rather than a weighted selection score.

### Periodic topology safety gate

Topology is evaluated only on explicitly preserved profile groups. The generated LTA campaign uses

```toml
relax_topology_group_ids = ["framework"]
```

so Li/Na/K guest relocation does not masquerade as framework damage. The core verifier is material-generic: other profiles may name any static profile-declared preserved groups; an empty Python-API group list means all atoms.

For each protected group, RELAX-VERIFY1 constructs the periodic minimum-image bonded graph using species-dependent ASE covalent-radius cutoffs multiplied by the frozen default scale `1.20`. The comparison uses persistent atom/species identities and unordered bonded pairs, not renderer/topology IDs or wrapped coordinates. Therefore harmless periodic wrapping does not change connectivity. The candidate must have

- the same protected vertices/species identities;
- the same bonded pair set as the DFT-relaxed reference;
- identical protected-atom coordination counts; and
- no new or missing protected-group bonds.

Because the full protected periodic edge graph is preserved, profile ring/cage connectivity derived from that same framework graph cannot change merely through topology-ID relabeling. A changed DFT reference graph is rejected before candidate comparison. A changed candidate graph is a hard safety failure independent of its geometric RMSE.

### Quantitative geometry fidelity

Passing topology is not sufficient. Candidate and DFT-relaxed structures are compared atom-by-atom under the periodic minimum image after removing only a harmless rigid translation of the protected group. No arbitrary rotation or permutation is fitted. Bond and angle errors are evaluated on the common protected reference graph.

First-release hard tolerances are:

| quantity | default hard tolerance |
|---|---:|
| protected-group RMS displacement | `0.15 A` |
| protected-group maximum displacement | `0.40 A` |
| protected-bond RMSE | `0.08 A` |
| protected-bond maximum absolute error | `0.20 A` |
| protected-angle RMSE | `8 deg` |
| protected-angle maximum absolute error | `20 deg` |
| fixed-cell strain norm | `1e-4` |
| final maximum force | `0.03 eV/A` |

Every common base is a hard gate. Metrics are not averaged across bases to hide one topology failure or one badly distorted relaxation. Thus a model may preserve framework connectivity yet still fail because it settles into a quantitatively wrong local minimum.

The completed run record freezes the PES authority, target-only model SHA-256, relaxation policy, base/request/reference identities, DFT protocol hashes, candidate relaxed ExtXYZ bytes, optimizer convergence evidence, topology changes, and every geometry metric. Reuse is permitted only when all of those identities still authenticate.

**Acceptance:** DFT and MLFF begin from identical frozen bases; the DFT reference is converged and topologically intact; periodic wrapping cannot create a false graph failure; every PES-qualified candidate must converge, preserve the declared protected graph, and satisfy all geometry tolerances on every common base. RELAX-VERIFY1 completion leaves `verify` waiting for DYN-VERIFY2 rather than granting production authority.

## Gate DYN-VERIFY2 - short structural dynamical qualification

**Implementation status (`0.20.175a0`): complete.** DYN-VERIFY2 is the final pre-selection physical gate. It consumes only candidates that have already passed DEPLOY-VERIFY1, PES-VERIFY1, and RELAX-VERIFY1, and it executes the exact deployed ML-IAP artifact through the same authenticated LAMMPS executable and launch arguments whose bytes were frozen by DEPLOY-VERIFY1. Static target RMSE, local finite-displacement correctness, and zero-K relaxation remain separate authorities; short-MD stability cannot substitute for any of them.

### Common rollout authority

The rollout authority is candidate-independent. It is built from the common DFT-relaxed RELAX-VERIFY1 reference cohort, retaining at most two correlation-balanced bases by default. All surviving candidates see the same base structures, temperatures, integration protocol, protected topology, velocity seeds, sample cadence, and numerical/structural thresholds. A candidate that passes or fails cannot change which rollout cases another candidate receives.

The first-release default case grid is:

| quantity | default |
|---|---:|
| common DFT-relaxed bases | at most `2` |
| temperatures | `300 K`, `800 K` |
| timestep | `0.5 fs` |
| thermostat stage | Langevin NVT, `400` steps = `0.2 ps` |
| Langevin damping | `100 fs` |
| production stage | NVE, `2000` steps = `1.0 ps` |
| sampling interval | `10` steps = `5 fs` |
| velocity-seed base | `314159` |

For each base/temperature pair, the exact deterministic velocity seed is frozen in the plan and reused across competing candidates. LAMMPS records an explicit `run 0` frame **before** velocity creation. Consequently the structural reference frame is exactly the common DFT-relaxed geometry rather than the first thermally displaced sample.

The NVT segment is only a bounded temperature-initialization stage. Structural and numerical qualification uses the full trajectory, while NVE energy drift is measured only on the unthermostatted segment. The first half of NVT is excluded from the mean-temperature diagnostic so the initialization transient cannot dominate that statistic.

### Numerical dynamics diagnostics

Every case must remain finite and satisfy all applicable numerical bounds:

| diagnostic | default hard bound |
|---|---:|
| absolute NVE total-energy drift | `<= 0.026 eV/atom/ps` |
| minimum interatomic distance | `>= 0.8 A` |
| maximum atomic force magnitude | `<= 100 eV/A` |
| NVT mean-temperature relative error | `<= 20%` |
| NVE mean-temperature relative error | `<= 30%` |

The minimum-distance calculation uses periodic minimum-image geometry; an expanded system with no pair inside the fast neighbor-list radius falls back to the exact periodic all-pairs minimum rather than being interpreted as an infinite separation. Missing/nonfinite force data are themselves a failed numerical case and cannot bypass the persistent-structure record.

These diagnostics are **necessary, not sufficient**. A wrong PES can conserve its own energy accurately. DYN-VERIFY2 therefore gives independent hard authority to persistent structural observables.

### Persistent structural-damage authority

Protected atoms/groups are inherited from RELAX-VERIFY1. In the generated LTA profile the preserved group is the zeolite `framework`, so mobile Li/Na/K motion does not falsely count as framework destruction.

A periodic reference bond graph is frozen from each common DFT-relaxed base using the same generic chemistry-aware connectivity machinery as RELAX-VERIFY1 with default topology cutoff scale `1.20`. During the rollout:

- a reference bond is considered broken when its instantaneous minimum-image length exceeds `1.35` times its frozen reference length;
- a new protected-group bond is detected using the tighter connectivity scale `1.10`;
- rigid translation is removed before protected-group displacement statistics are evaluated;
- protected-group bond and angle distortions are computed relative to the same relaxed reference.

A sampled frame is marked structurally damaged when any one of the following occurs:

| structural observable | default damage threshold |
|---|---:|
| missing frozen reference bond | bond length `> 1.35 x` reference |
| new protected bond | connectivity scale `1.10` |
| protected-group RMS displacement | `> 0.60 A` |
| protected-group maximum displacement | `> 1.50 A` |
| protected-bond RMSE | `> 0.15 A` |
| protected-angle RMSE | `> 15 deg` |

A single thermal excursion is **not** a hard failure. Structural damage becomes a DYN-VERIFY2 failure only when the damage flag persists for at least `10` consecutive saved samples. With the default 5 fs sample cadence this is a `50 fs` persistence requirement. This distinguishes ordinary bond-length/angle flicker from a genuine transition into a damaged framework/motif basin while still making persistent framework breakage a hard failure.

Every generated base/temperature case is a hard gate by default. Results are not averaged across temperatures or bases to hide one damaged rollout. A candidate passes DYN-VERIFY2 only when every required case passes both the numerical and persistent-structure authorities.

### Deployment and restart provenance

Each run record freezes at minimum:

- RELAX-VERIFY1 run and common-reference identities;
- DEPLOY-VERIFY1 run identity;
- exact ML-IAP deployment artifact path and SHA-256;
- exact LAMMPS executable path, SHA-256, and launch arguments;
- DYN policy and common-plan digests;
- base/temperature/velocity-seed identity for every case;
- trajectory and log paths plus SHA-256;
- temperature, energy-drift, minimum-distance, force, displacement, bond, angle, and persistence metrics; and
- explicit per-case failure reasons.

Cached evidence is reusable only while all upstream, executable, deployment-artifact, policy, case-membership, trajectory, and log identities still authenticate. Changing the LAMMPS binary, ML-IAP artifact, common relaxed reference, rollout policy, or case membership forces fresh dynamical verification.

### Stage-C handoff

DYN-VERIFY2 has direct target-size-decision responsibility. During TARGET-DATA2D Stage C, it creates authenticated physical-qualification evidence for **both** target-size finalists. A finalist passes physical qualification only when DEPLOY-VERIFY1, PES-VERIFY1, RELAX-VERIFY1, and DYN-VERIFY2 all pass. That hard pass/fail chain is attached to the existing 30-of-30 static EVAL2 evidence and supplied to TARGET-DATA2D. If Stage C reaches `selected`, TARGET-DATA2E can then materialize the immutable production target corpus. If the largest bounded rung remains materially better, the existing non-convergence rule remains authoritative; DYN cannot manufacture convergence.

After the production-size training matrix is complete, DYN-VERIFY2 similarly qualifies the final-development seed candidates but deliberately leaves the overall workflow waiting for SELECT2. DYN is a qualification gate, not a seed-ranking score.

**Acceptance:** deployment-parity, PES, and relaxation qualification precede interpretation of short-MD stability; all required common cases use the same candidate-independent rollout authority; numerical NVE/NVT stability cannot compensate for persistent protected-structure damage; transient thermal excursions below the frozen persistence window do not create false failures; exact deployed ML-IAP/LAMMPS bytes are authenticated; Stage-C physical evidence is bound back to TARGET-DATA2D; and DYN pass/fail receives no positive ranking weight in SELECT2.


## Gate SELECT2 - physics-qualified lexicographic production selection

**Implementation status (`0.20.176a0`): complete.** SELECT2 consumes only the selected-size final-development seed representatives after production EVAL2 and the complete DEPLOY-VERIFY1 -> PES-VERIFY1 -> RELAX-VERIFY1 -> DYN-VERIFY2 chain. It first freezes a replay-independent static seed order using the exact EVAL2 practical-equivalence/bootstrap and target-secondary policy, then applies physical pass/fail as a filter over that already-frozen order. The first physical passer is copied byte-for-byte into a `models/select2-frozen/` pre-locked-test location together with its exact ML-IAP deployment artifact. The resulting authority is a frozen production **candidate**, not evidence that the locked test passed; the subsequent one-shot locked test may evaluate these bytes but may not choose another checkpoint or seed.

Static target RMSE is necessary but cannot by itself publish a production model. A candidate enters the
final production comparison only after passing, in order, all applicable hard authorities established
above:

1. numerically valid completed TRAIN2 trajectory;
2. full target hard thresholds;
3. authenticated foundation-relative replay-retention ceiling;
4. DEPLOY-VERIFY1 target-head/export/deployment parity;
5. PES-VERIFY1 restoring-force/local-curvature qualification;
6. RELAX-VERIFY1 topology preservation and geometry fidelity; and
7. DYN-VERIFY2 short structural dynamical qualification.

PES, relaxation, and short-rollout results are **qualification gates**, not arbitrarily weighted terms in
a static-error score. In particular, a model with lower target RMSE but framework/motif damage in the
frozen short structural rollout is ineligible; it cannot defeat a slightly higher-RMSE model that passes
the physical qualification protocol.

SELECT2 freezes the final-development seed order **before** physical pass/fail is consulted. The static order uses the same frozen lexicographic target ordering as EVAL2:

```text
1. minimize full target S_target
2. if practically/statistically indistinguishable, minimize max_c RMSE_c over applicable target strata
3. if still indistinguishable, minimize species-macro force RMSE
4. if still indistinguishable, minimize target force-error P95
5. if still indistinguishable, minimize target force-error P99
6. for checkpoint ties within a run, prefer the later/lower-LR refinement checkpoint
7. if still tied, use frozen stable candidate identity
```

The same unrounded 1 meV/A practical-equivalence rule and deterministic EVAL2 paired-bootstrap policy
(2000 paired correlation-block resamples, 95% percentile interval, minimum 10 independent blocks, seed
derived from evaluation-plan identity) apply to target checkpoint/seed comparisons unless an explicitly
versioned profile states otherwise. Non-applicable secondary target diagnostics are skipped rather than
imputed. Across final optimizer seeds, the maturity tie-break is usually already resolved inside each run,
so target strata/species/tails and a stable replay-independent identity resolve any remaining exact tie.

Physical qualification then acts only as eligibility over that frozen static order. SELECT2 walks the
pre-ranked final-development seed representatives and selects the first candidate whose complete
DEPLOY/PES/RELAX/DYN chain passes. Failed higher-ranked candidates remain in the immutable SELECT2 record,
and the exact number of skipped candidates is stored as `fallback_count`; physical metrics never reshape
the target order. This deterministic bounded fallback is completed **before** the one-shot locked test is
activated. Within each seed, EVAL2 has already completed its bounded target-ranked checkpoint rescue and
frozen one admissible run representative before physical verification begins. The locked test evaluates
the already frozen production candidate and has zero authority to select a different checkpoint or seed.

Tail checkpoint averaging may be implemented later as an explicit experimental candidate-generation
mode, but it is disabled by default until separately qualified for force/energy consistency, deployment
parity, and reproducibility.

**Acceptance:** no production candidate can be frozen by static RMSE alone; short-rollout structural
damage is a hard failure where the material profile declares preserved motifs/frameworks; the static
cross-seed order is frozen before physical filtering; fallback is bounded and follows that target-first
order without reranking; replay never rescues worse target physics; selected target-only and ML-IAP bytes
are atomically frozen and authenticated; and the locked test remains one-shot, post-selection evidence with
zero authority to select an alternative.

## Gate LOCKED-TEST2 - one-shot locked post-freeze test and final production publication

**Implementation status (`0.20.177a0`): complete.** LOCKED-TEST2 activates only after SELECT2 has
frozen exactly one pre-ranked, physically qualified production candidate. It materializes the sealed
`locked_interpolation_test` role for the selected label domain exactly once, freezes that locked-E byte
identity before inference, evaluates only the already frozen target-only model, and can return only
`pass` or `fail`. It has no API or control path for ranking, fallback, retraining, target-size selection,
checkpoint rescue, replay scoring, or alternative seed selection.

### One-shot activation authority

The activation record binds, before locked inference begins:

- campaign and SELECT2 selection/frozen-candidate identities;
- TARGET-DATA2A role-freeze and sealed DATA8 locked-E role identities;
- exact selected run, optimizer seed, label domain, target-only model SHA-256, and ML-IAP SHA-256;
- exact locked-E ExtXYZ bytes, frame membership, correlation-unit membership, and per-frame block IDs;
- the resolved LOCKED-TEST2 policy; and
- the activation timestamp for audit only.

The default hard criterion is the same full target force-RMSE ceiling frozen by TRAIN2 admissibility,
which is `0.030 eV/A` (30 meV/A) for generated defaults. Optional locked-only ceilings may be declared
for energy MAE/atom, worst target-stratum force RMSE, target force-error P99, and stress RMSE. These
additional metrics remain pass/fail authorities only; they never create a score or a comparison with an
alternative candidate. Replay is absent from LOCKED-TEST2 by construction.

The complete EVAL2 target metric reducer is reused for diagnostics so the locked record retains global,
per-species, species-macro, tail, energy, stress, and applicable stratum evidence. Correlation-block
identities are retained for audit, but there is no bootstrap model-selection operation at this stage:
SELECT2 already completed all permitted comparison before locked E was exposed.

### No second look

Once the activation record exists, the locked-E artifact is never rematerialized or overwritten. A rerun
may only authenticate and reuse the exact frozen bytes. If the locked data, policy, SELECT2 candidate,
role lineage, correlation mapping, target-only model, or ML-IAP bytes change or disappear after
activation, the campaign fails closed and requires a new campaign/protocol identity. A crash after
activation but before result persistence may resume the same evaluation on the exact same bytes; it may
not create a new scientific activation.

### Final publication

If locked E fails, `verify` becomes `FAILED`, the SELECT2 candidate remains frozen for audit, and no
production model is published. The campaign may not try the next seed/checkpoint/rung. Any scientific
response to that failure belongs to a new protocol/data generation.

If locked E passes, final publication is byte preserving. The exact frozen SELECT2 target-only model is
atomically published as `models/production_best.model` and the exact DEPLOY-authenticated ML-IAP bytes as
`models/production_best-mliap_lammps.pt`. The final production authority freezes campaign, SELECT2,
locked activation/result, run/seed/checkpoint, destination paths, SHA-256 values, byte sizes, and
publication timestamp. Once that authority exists, changed or missing published bytes are corruption, not
a reason to silently republish a different candidate. `verify` reaches `COMPLETE` only after this record
authenticates.

**Acceptance:** locked E is unseen until one SELECT2 candidate is frozen; activation precedes inference;
the exact sealed role and bytes are immutable after activation; default target force RMSE is bounded by
the TRAIN2 full-target ceiling; optional locked diagnostics have pass/fail authority only; replay,
fallback, reranking, and alternative selection are impossible; failure publishes nothing; success
publishes byte-identical SELECT2/DEPLOY artifacts with immutable provenance; and any later training or
enrichment motivated by locked evidence starts a new campaign/protocol identity.

## Gate AL2 - failure-onset and uncertainty-driven target enrichment

When verified deployment parity proves that a physical failure belongs to the candidate PES, failed
MLFF trajectories may seed a new active-learning generation. Selection emphasizes the **onset** of
failure rather than flooding the corpus with completely destroyed structures:

```text
intact -> distorted -> incipient coordination/bond failure -> first break -> damaged
```

High-priority candidates combine committee/model disagreement, structural novelty, underrepresented
bond/angle/coordination tails, local-environment extrema, and profile-declared transition physics.
Fully broken structures may be retained sparsely as negative examples.

Every promoted DFT point records whether it came from the original unbiased corpus, a finite-displacement
probe, a foundation-failure correction, or a later AL generation. Per-generation quotas/caps prevent a
single pathological campaign from dominating the target distribution.

**Acceptance:** AL lineage is immutable; challenge/locked evidence is not silently recycled into the
same campaign; promotion starts a new versioned target-selection identity.

## Frozen challenge/qualification corpus

Maintain a small untouched challenge corpus containing difficult but physically valid examples such
as high-temperature tails, large valid strains, rare coordination environments, finite-displacement
probes, and migration/transition environments. It is not used for lightweight checkpoint ranking.
Its role is to measure whether robustness improves across protocol/data generations rather than merely
whether the monitor was optimized.

## Revised authority order

For new campaigns after this roadmap closes, the intended authority is:

```text
TARGET-DATA2A role freeze
        -> FOUNDATION-AUDIT1 role-scoped zero-shot baseline
        -> TARGET-DATA2B/C/D/E
        -> TRAIN2A/B fixed-budget deterministic optimization
        -> EVAL2 target-first checkpoint shortlist/full evaluation
        -> replay hard-retention gate
        -> DEPLOY-VERIFY1 parity
        -> PES-VERIFY1 local restoring-force qualification
        -> RELAX-VERIFY1 topology + geometry qualification
        -> DYN-VERIFY2 short structural dynamics
        -> SELECT2 physics-qualified lexicographic production selection
        -> LOCKED-TEST2 one-shot locked test + final byte-preserving publication
        -> AL2 next-generation enrichment when required
```

LOCKED-TEST2 is strictly post-fallback and post-freeze: it may accept or reject the one frozen
production candidate but can never choose an alternative checkpoint/seed/target size. Its result is the
last authority before final production publication.

## Completion criteria for this revision

The roadmap is complete only when all of the following are demonstrated end to end:

1. default generated geometry is `2 seeds x (3 folds + 1 final) = 8` runs for protocol development,
   while seed extension remains available before production freeze;
2. lightweight checkpoint monitors remain at the existing defaults of 256 target and 512 TRUE_DFT
   replay configurations unless separately requalified;
3. independent validation/locked/challenge roles are frozen before any evidence used to choose
   `N_target`, and target-size selection consumes only its authorized training-eligible development
   domain;
4. target selection is physics-stratified, deterministic, materially generic by default, and emits one
   immutable nested `2^7` through `2^13` ranked-prefix ladder;
5. bond-length, angle, coordination, local-distortion, and local-extreme coverage is species/pair/
   triplet normalized rather than atom-count biased;
6. element/material/foundation-specific selection weights exist only in explicit profiles/overrides;
7. the Stage-A reference is computed from the entire authorized training-eligible target pool, each
   required coverage family independently satisfies the default 95% criterion, and every declared scalar
   extent channel reaches the weighted Q01/Q99 reference envelope with no generated numerical tolerance;
8. Stage A retains **every** hard-coverage-qualified rung, performs no economic size ranking, and raises
   a hard coverage/data-adequacy error when fewer than three pass;
9. Stage B0 observes every hard-coverage-qualified rung at exactly 3 completed epochs on the original
   30-epoch schedule, strictly after LR warm-up, uses one common leakage-safe target-only coarse role,
   performs no replay inference, and retains at most four using target-only evidence plus boundary-preserving
   practical equivalence;
10. Stage B1 resumes the epoch-3 survivors to exactly 10 completed epochs, proves checkpoint/optimizer/RNG
    ancestry, treats TRUE_DFT replay as diagnostic-only with zero ranking credit, and retains exactly two
    finalists while preserving the largest ladder boundary only within its practical-equivalence band;
11. Stage C resumes those finalists to 30 total epochs under restart-equivalent checkpoint/optimizer/RNG/
    scheduler/LR state, completes the mandatory refinement tail, restores smaller-size preference within
    final practical equivalence, and combines target, PES, relaxation, topology, geometry, deployment,
    dynamics, and hard replay-admissibility evidence to select one size;
12. a materially improving largest rung is reported as non-convergence within the bounded ladder rather
    than silently declared converged;
13. replay degradation has hard pass/fail authority but exactly zero checkpoint/final-seed/target-size
    composite-score contribution;
14. every numerically valid TRAIN2 run completes its prescribed budget; target/replay monitor crossings,
    patience, and validation plateaus cannot terminate training or mutate LR;
15. the generated LR trajectory is update-normalized and deterministic, using `p_u = u/(U-1)` and the
    frozen piecewise linear/cosine multiplier defined by TRAIN2B (default 5%/75%/20% and relative LR scales
    0.10 -> 1.00 -> 0.10 -> 0.01), advances exactly once per optimizer update, and cannot compete with a
    second native/adaptive LR scheduler;
16. checkpoint full-evaluation purchase is target-first and includes mature refinement candidates rather
    than allowing a transient earlier validation minimum to monopolize the shortlist;
17. target evaluation reports global, species-macro, per-species, tail, energy, force, and stress
    evidence as applicable;
18. checkpoint comparisons use the unrounded 1 meV/A practical-equivalence scale and, when at least 10
    independent frozen correlation blocks exist, a deterministic paired 2000-replicate 95% percentile
    bootstrap; indistinguishable secondary target evidence is ordered lexicographically by worst stratum,
    species-macro RMSE, P95, then P99 before checkpoint maturity and the stable replay-independent exact tie-break;
19. selected target-head, exported model, and deployment artifact demonstrate numerical parity before
    physical conclusions are drawn;
20. finite-displacement probes detect wrong local restoring forces/curvature;
21. zero-K relaxation preserves the required periodic framework/motif graph and reproduces target
    geometry within declared tolerances;
22. short MD cannot pass after structural damage simply because energy drift is small, and a static-
    RMSE winner that fails the structural rollout is ineligible for production;
23. final production selection is lexicographic over physically qualified candidates: target quality
    first, then target tails/worst strata, then checkpoint maturity where applicable, with replay used
    only as the hard admissibility constraint and never as a ranking or tie-break reward;
24. bounded physical fallback follows a frozen target-first candidate order and completes before the
    one-shot locked test is activated;
25. LOCKED-TEST2 activates exactly once on the already frozen SELECT2 bytes, can only pass or fail,
    cannot rematerialize changed locked evidence or select an alternative, publishes nothing on failure,
    and on success publishes byte-identical target-only MACE and ML-IAP artifacts with immutable hashes;
26. active-learning corrections preserve generation/source lineage and cannot silently contaminate
    frozen challenge/locked evidence; and
27. historical campaign identities, `AdaptiveTrainingStopPolicy` behavior, early-stop behavior, scores,
    and replay-weighted semantics remain readable under the exact authority that created them rather than
    being silently reinterpreted; new campaigns freeze separate `TrainingBudgetPolicy`,
    `LearningRateSchedulePolicy`, `CheckpointAdmissibilityPolicy`, and `CheckpointSelectionPolicy` identities,
    and mixed historical/new control schemas fail closed.

This revision intentionally treats the observed LTA/MPA-0 failure as a **diagnostic case**, not a
source of generic chemical bias. The generic protocol must be capable of discovering the analogous
failure in an unseen material or a different foundation model without prior knowledge of which
species/environment will be vulnerable.

### Revision closure after LOCKED-TEST2

The TARGET-DATA2/TRAIN2/EVAL2 policy, DEPLOY-VERIFY1, PES-VERIFY1, RELAX-VERIFY1, DYN-VERIFY2, SELECT2,
and the one-shot LOCKED-TEST2/final-publication protocol are now implemented with frozen scientific rules
and restart/provenance authority. This closes the first-release production-selection sequence. AL2 remains
a later-generation path when locked/challenge/physical evidence motivates new DFT training data; such
feedback starts a new campaign/protocol identity and never reopens the completed locked test.

## Deferred or intentionally unchanged work

The current DATA6/DATA7 production architecture is not scheduled for another broad
algorithm rewrite in this optimization cycle.  DATA6 is sharded/streaming, DATA7
selection uses bounded `O(N K d)` farthest-point-style work, and shared DATA7
artifacts already eliminate many seed/mode recomputations.  The remaining
scientifically intentional atomic-geometry feature work can scale approximately as
`O(N A^2)` for `N` frames and `A` atoms per frame; replacing that representation
would change the feature definition and therefore requires a separately versioned
large-supercell selection policy rather than a transparent performance patch.

## Completion rule

Each optimization stage must be specified, implemented, and tested independently.
A stage is complete only when:

1. its new runtime/cache contracts are documented;
2. restart and corruption behavior are tested;
3. scientific evaluation/selection identities are unchanged unless explicitly
   versioned;
4. numerical equivalence or acceptance tests pass;
5. representative timing evidence demonstrates the intended improvement; and
6. the legacy fallback, when retained, remains fail-closed and clearly reported.

The staged optimization roadmap **OPT-EVAL1 through OPT-CTRL1 is complete**. The
post-0.20.105 multi-fidelity-evaluation/staged-precision/storage roadmap above is a
separate cycle opened by new production-scale profiling, FP64-training, and storage
evidence. `EVAL-MF1`, `EVAL-MF2`, `PREC1`, `PREC2`, `PREC3`, `STOR1`, `STOR2`, `STOR3`, `STOR4`, and `STOR5` are implemented through 0.20.116a0; this roadmap is closed.



## Append-only optimizer-seed extension (0.20.155a0)

A completed conventional MLCV campaign may be extended before VERIFY1 by adding one optimizer seed without retraining or re-evaluating prior seeds. The supported user operation is:

```bash
mdstats-mlff-campaign --config campaign.toml extend-seed --seed 4
```

The operation is intentionally narrow: `mlcv_nested_cv`, `seed_mode = "optimizer_only"`, at least two CV folds, and one configured selection size. The new DATA8 variant must reproduce the exact parent `MlcvRoleCatalog` digest, so all seeds use the same fold roles and only stochastic MACE optimizer/training realization changes.

Before reopening the campaign, mdstats archives the parent training-campaign plan and campaign-level MLCV authority under content-addressed historical seed-extension records. Existing run-local execution, ranking, SELECT1, candidate-evaluation, and outer-fold records remain canonical because their run-plan identities are unchanged. Campaign-level lifecycle, seed-CV, campaign-CV, FINAL1 selection, and committee records are regenerated because their lineage includes the campaign-plan digest. Verified promoted DATA7 archives from reused parent variants are re-registered as exact shared recipe artifacts before the new variant is materialized, so optimizer-only extension does not depend on the transient `.mdstats/data7-cache` surviving post-training cleanup. Thus an `N`-seed campaign extended to `N+1` buys only the new seed's `K` fold fits plus one final-development fit and the corresponding new inference; prior seeds are reused.

Extension is forbidden after VERIFY1, locked-E, production-model publication, MLCV protocol freeze/migration, or generic protocol-freeze authority. At that point the production evidence graph is scientifically frozen and a new campaign identity is required. The appended seed enters FINAL1 only if it independently qualifies under the unchanged target/replay/CV policies.

The `train` command consequently supports `--training-mode`, `--seed`, and `--selection-size` filters, allowing exact scheduling of the appended seed variant.

# Post-0.20.177 generalized MACE foundation-model and MH-1 support revision

**Historical staged status (pre-workstation qualification):** architecture frozen for staged implementation after `mdstats 0.20.177a0`; no gate in this section is considered implemented until its implementation record is appended below the corresponding gate. This revision generalizes the MLFF branch from an implicit MPA-0-oriented foundation contract to an explicit MACE foundation-model/head contract. It preserves MPA-0 as a fully supported single-head foundation while making **MACE-MH-1 + `omat_pbe` + cuEquivariance-based acceleration** the generated campaign default. The ordinary e3nn implementation remains a first-class, fully tested production/reference backend and is the numerical authority used to qualify accelerated MH-1 inference.

This revision does **not** change the completed TARGET-DATA2/TRAIN2/EVAL2/DEPLOY/PES/RELAX/DYN/SELECT2/LOCKED-TEST2 scientific selection rules. It changes the identity, realization, compatibility, replay provenance, and execution contracts required to run those rules against a genuinely multi-head MACE foundation model.


> **Current runtime authority after post-CERT1 qualification (2026-08-15).** The opening CONFIG1/CERT1 language in this section records the original staged revision intent and is retained as historical implementation context. It is **not** the current generated-backend authority for MH-1. Real RTX 3090 qualification subsequently showed that the original six-head MH-1/`omat_pbe` checkpoint is not numerically equivalent under the tested CuEq realizations. The binding generated default is therefore **MH-1/`omat_pbe`/e3nn**. e3nn is the production/reference backend for source-foundation inference, DATA6, pseudolabel generation, evaluation, and the first complete campaign baseline. CuEq remains an explicit, fail-closed experimental backend. Any future CuEq authorization must proceed through the separate post-CERT optimization gates defined below; it may not be inferred from historical CONFIG1/CERT1 completion text, accelerator availability, or the much smaller discrepancy observed on the EXTRACT1-derived single-head training foundation.

## Motivation and observed development fixtures

The pre-0.20.177 MLFF implementation correctly carries an explicit `foundation_head` through parts of DATA8 and several protocol artifacts, but foundation identity is not yet uniform across the branch. In particular, the DATA6-side `ModelCheckpointIdentity` remains head-blind, several replay/reference-fit/materialization contracts still bind only checkpoint SHA-level provenance, some calculator construction paths do not bind the configured source head, and accelerator identity knows only a coarse e3nn/cuEquivariance choice. Those assumptions are survivable for a true single-head MPA-0 checkpoint and become scientifically ambiguous for MACE-MH-1.

The development fixtures supplied for this revision establish the following concrete compatibility target. Their SHA values are **test-fixture identities only** and are not production requirements; production code must inspect arbitrary compatible checkpoints rather than recognize filenames or fixed hashes.

| Property | supplied MACE-MH-1 | supplied MACE-MPA-0-medium |
|---|---|---|
| model class | `ScaleShiftMACE` | `ScaleShiftMACE` |
| checkpoint role | multi-head foundation | single-head foundation |
| available heads | `matpes_r2scan`, `mp_pbe_refit_add`, `spice_wB97M`, `oc20_usemppbe`, `omol`, `omat_pbe` | `default` |
| generated default source head | `omat_pbe` | intrinsic singleton `default` |
| supported element table | 89 atomic numbers | 89 atomic numbers |
| cutoff | 6.0 A | 6.0 A |
| interaction count | 2 | 2 |
| characteristic node width | 512 | 128 |
| explicit edge representation | `128x0e+128x1o` | older architecture without the MH-1 explicit edge representation |
| interaction family | nonlinear/agnostic residual architecture | older density-interaction architecture |
| invariant descriptor width observed through MACE API | 1024 values/atom | 256 values/atom |
| full descriptor width observed through MACE API | 2560 values/atom | 640 values/atom |

The supplied MACE 0.3.16 source can load and evaluate the MH-1 checkpoint through e3nn, but its stock selected-head `remove_pt_head()` reconstruction fails for the supplied MH-1 checkpoint for at least `omat_pbe` and `omol`. The failure is a model-reconstruction/state-dictionary shape mismatch in the first nonlinear interaction (including a 4x mismatch in `interactions.0.linear_up.weight`), not a failure to read the original checkpoint. Therefore selected-head extraction is a **known compatibility gate**, not a hypothetical late-stage risk.

The same MH-1 fixture also demonstrates that descriptor dimensionality is materially larger than MPA-0 even though raw parameter count is not a reliable predictor of inference memory. DATA6 batching and storage therefore require model-aware calibration rather than continued reliance on MPA-era fixed memory estimates alone.

## Frozen default and compatibility policy

After this revision is implemented, newly generated campaigns use the following defaults unless explicitly overridden:

```toml
[foundation]
family = "mace_mh_1"
head = "omat_pbe"

[acceleration]
backend = "cueq"
```

The binding rules are:

1. **foundation-model identity is checkpoint- and head-qualified** - a multi-head checkpoint is not a complete scientific identity until an exact source head has been resolved;
2. **checkpoint introspection is authoritative** - filenames, static published head lists, and human-readable `foundation_name` strings may not determine scientific identity;
3. **MPA-0 remains fully supported** - a demonstrably single-head legacy checkpoint may normalize its singleton head automatically;
4. **MH-1 is fail-closed on head ambiguity** - an omitted or invalid head on a multi-head foundation raises a hard error and reports the heads actually present in the checkpoint;
5. **no calculator fallback authority** - mdstats resolves and validates the requested head before constructing `MACECalculator`; any MACE-internal warning/fallback behavior is not accepted as campaign semantics;
6. **three head namespaces are distinct** - `foundation_head` identifies the immutable source foundation head, `target_head` identifies the learned target/adaptation head, and `pt_head` identifies the replay/preservation head;
7. **cuEquivariance is the generated default, not an implicit machine-dependent choice** - `init` writes the requested CuEq policy even when the initialization host lacks the accelerator; `doctor` qualifies the requested execution environment later;
8. **e3nn is first-class** - e3nn must support the complete prepare/train/evaluate/verify/deploy path and serves as the numerical reference for accelerated-foundation qualification;
9. **no silent CuEq-to-e3nn fallback** - if a CuEq campaign cannot be qualified, doctor fails and the user must explicitly select `backend = "e3nn"`;
10. **CuEq implementation mode is resolved and frozen** - the user-facing backend remains `cueq`, while the realized kernel path may be pure CuEq or the MACE-supported CuEq/OpenEquivariance hybrid when required by model architecture; the resolved mode is explicit evidence and may not change silently across campaign phases;
11. **scientific and execution identities are separate** - e3nn and CuEq realizations of the same checkpoint/head remain the same physical foundation potential but are distinct inference/cache/generator realizations;
12. **historical evidence is never reinterpreted by guesswork** - head-blind historical artifacts may normalize only when the referenced foundation is demonstrably single-head; ambiguous multi-head history fails closed;
13. **MPA-0 pseudolabel values are not MH-1 replay labels** - existing replay geometries may be reused, but foundation-generated energies/forces/stresses are regenerated and rebound when the foundation/head/generator changes;
14. **upstream checkpoints remain immutable** - any MACE-0.3.16 compatibility extraction produces a derived artifact with explicit source SHA/head/shim provenance; mdstats never patches the installed MACE package or overwrites the original model file; and
15. **future corrections remain composable** - scientific foundation identity may carry an empty versioned correction stack so later long-range/electrostatic corrections can extend identity without another root redesign, but this revision implements no new physical correction term.

## Canonical foundation and inference identities

The existing `FoundationCheckpointIdentity` and DATA6 `ModelCheckpointIdentity` must converge on one shared foundation contract instead of evolving as parallel, partially overlapping identities.

### Scientific foundation identity

A new foundation module should own the canonical inspection and identity objects, conceptually:

```text
MaceFoundationSpec
    family
    requested_head

MaceFoundationInspection
    checkpoint_sha256
    model_class
    available_heads
    model_atomic_numbers
    r_max
    num_interactions
    serialized_architecture_signature
    model_dtype

FoundationPotentialIdentity
    checkpoint_sha256
    family
    resolved_head
    available_head_signature
    model_class
    model_atomic_numbers
    serialized_architecture_signature
    correction_stack = ()
```

`FoundationPotentialIdentity` is the scientific authority for questions such as which foundation generated a residual E0 fit, which source head DATA8 adapts, and whether two pseudolabel corpora represent the same foundation potential.

The existing `protocol.FoundationCheckpointIdentity` should advance to a new schema and become a serialization/public-export surface for this canonical object rather than remain an independently implemented identity.

### Execution/inference identity

A distinct execution identity extends the scientific identity with numerically relevant realization state:

```text
FoundationInferenceIdentity
    foundation_potential_identity_digest
    MACE runtime version
    dtype
    requested backend
    resolved accelerator mode
    descriptor adapter version
    descriptor policy version
```

DATA6 model-feature caches, foundation prediction caches, accelerator parity evidence, and foundation pseudolabel generator provenance bind to this execution identity. Two backends may represent the same physical foundation potential while remaining non-interchangeable cached numerical realizations.

### Requested versus supported species

The current DATA6-side use of campaign/profile atomic numbers as `supported_atomic_numbers` must be removed. The architecture records both:

```text
model_supported_atomic_numbers
requested_atomic_numbers
```

and enforces the generic requirement:

```text
requested_atomic_numbers subset_of model_supported_atomic_numbers
```

No MPA-0- or MH-1-specific species whitelist is required for the present 89-element fixtures.

## Serialized architecture fidelity and selected-head reconstruction

Checkpoint-faithful architecture inspection is required before selected-head extraction. A generic MACE configuration reconstructed only from high-level helper output is not sufficient evidence when the serialized MH-1 architecture contains edge/intermediate representation information that the generic reconstruction path can lose.

The foundation inspector therefore records a `SerializedMaceArchitectureSignature` with enough information to distinguish at least:

- model class;
- node embedding irreps;
- interaction count and per-interaction class;
- per-interaction node, hidden, edge, target, and `linear_up` input/output irreps where available;
- product class and input/output irreps;
- readout classes and hidden irreps;
- `use_agnostic_product` and related nonlinear architecture flags;
- edge-irrep-first/non-uniform-edge behavior required for faithful reconstruction; and
- the observed state-dictionary tensor-shape signature for reconstruction-critical tensors.

Selected-head extraction emits a separate `ReconstructionCompatibilityRecord` containing source architecture digest, reconstructed architecture digest, state-dictionary-shape compatibility, applied compatibility-shim identity if any, and numerical parity evidence.

For the MACE 0.3.16 MH-1 defect, mdstats may implement only a **minimal, version-guarded compatibility correction** that reconstructs the exact serialized architecture required by the supplied MH-1 family. The shim must apply only to the affected MACE/version/architecture conditions, must create a new derived checkpoint, and must self-disable automatically when a future MACE release performs faithful stock extraction.

A derived selected-head checkpoint is not training-qualified merely because it loads. It must reproduce the original multi-head model evaluated explicitly at the selected source head for:

- total energy;
- atomic forces;
- stress;
- atomic E0 table/scale-shift semantics as applicable; and
- descriptors used by DATA6.

Only a parity-qualified derived `omat_pbe` checkpoint may enter DATA8 training when stock MACE 0.3.16 extraction is incompatible.

## Accelerator realization policy

The public campaign choice remains deliberately small:

```text
backend = cueq | e3nn
```

For `backend = cueq`, doctor may resolve one of the version-qualified MACE kernel implementations:

```text
cueq_pure
cueq_oeq_hybrid
```

OpenEquivariance is therefore an implementation dependency/realization component, not a third foundation or mandatory user-facing backend. The resolved mode is frozen in `AccelerationRealizationRecord` and contributes to `FoundationInferenceIdentity`.

A CuEq realization is authorized only when the corresponding e3nn reference realization succeeds and paired parity on a deterministic qualification corpus satisfies the declared numerical policy. At minimum, parity evidence includes:

- energy per atom;
- force RMSE and maximum absolute force difference;
- stress RMSE and maximum absolute stress difference;
- invariant/full descriptor differences where used by DATA6; and
- DATA6 selection stability on a deterministic qualification pool.

The last requirement is deliberately stronger than a finite-output smoke test. A backend difference too small to matter for energies may still be unacceptable if it materially changes the descriptors or selected training frames. Numerical tolerances should reuse/extend the existing deployment-parity philosophy rather than introduce an unrelated accelerator-specific tolerance system. Bitwise equality of independently trained CuEq/e3nn networks is **not** required; the parity authority applies to the common starting foundation inference/descriptor realization and to each backend's independent runtime correctness.

## Legacy artifact migration

Schema advancement is paired with controlled historical normalization. Every reader that advances a foundation-sensitive schema must either support its historical predecessor or document why the predecessor cannot be normalized safely.

The general rule is:

```text
historical head-blind artifact
        |
        v
inspect authenticated referenced checkpoint
        |
        +-- demonstrably single-head --> normalize to exact singleton identity
        |
        +-- multi-head/unknown --------> reject as scientifically ambiguous
```

Thus authenticated historical MPA-0 artifacts can remain readable because the source checkpoint is a true singleton. No migration code may infer `omat_pbe`, choose the first head, choose the last head, or trust a filename for an ambiguous multi-head artifact.

Migration changes interpretation only where the old artifact's meaning is provably unique; historical scores, stopping rules, DATA7 choices, locked evidence, and production bytes otherwise remain under the authority that created them.

## Gate MH1-DEP0 - dependency/runtime freeze

Before modifying production behavior, freeze and qualify the development runtime used by the MH-1 revision. The initial supported dependency target is:

- MACE `0.3.16`;
- e3nn `0.4.4` as required by that MACE line;
- the already qualified project Torch/CUDA stack rather than an unrelated opportunistic Torch upgrade;
- cuEquivariance packages compatible with the selected CUDA stack; and
- OpenEquivariance for the MACE-supported hybrid path.

The dependency bundle must be content-addressed/version-recorded. GitHub `main` is not a production dependency target merely because it is newer than the latest tagged release. A future tagged MACE release is adopted only after rerunning the foundation qualification matrix, especially selected-head extraction, CuEq/e3nn parity, one-epoch MH-1 multi-head replay training, and target-head deployment export.

### MH1-DEP0 code/evidence changes

- extend dependency/environment qualification evidence with CuEq and OpenEquivariance versions/capabilities;
- freeze the exact MACE source compatibility digest used by DATA8/realization checks;
- add an environment-level acceleration capability record without silently mutating generated campaign policy.

### MH1-DEP0 acceptance gate

1. MACE/e3nn/Torch/CUDA identities are explicit and reproducible;
2. CuEq and OEQ availability can be probed independently;
3. the environment can load both supplied real foundation fixtures through the e3nn reference path; and
4. lack of CuEq/OEQ produces an explicit capability failure for a CuEq campaign, not a fallback mutation.

### MH1-DEP0 implementation record - 2026-08-14

**Implementation status: complete for the runtime-freeze/evidence contract.** The supplied dependency archive is explicitly recorded as **e3nn-qualified but CuEq/OEQ-incomplete**; it is therefore not an authorizing dependency bundle for the later default CuEq campaign. This is a valid fail-closed DEP0 result rather than an implicit backend change. CuEq production qualification remains a later `MH1-ACCEL1` requirement and requires a CUDA environment containing the accelerator packages.

Implemented runtime contracts:

- new `mdstats/training_data/mace_runtime_freeze.py`;
- `MaceRuntimeFreezePolicy` / `MaceRuntimeFreezeRecord` and nested component, source, and checkpoint-load evidence schemas;
- exact MACE `0.3.16` source locking for `run_train.py`, `train.py`, `multihead_tools.py`, `scripts_utils.py`, `mace.py`, `arg_parser.py`, `convert_e3nn_hybrid.py`, and `convert_e3nn_oeq.py`;
- independent import/version capability probes for `cuequivariance`, `cuequivariance_torch`, `cuequivariance_ops_torch`, and `openequivariance`;
- explicit e3nn checkpoint-load evidence with a requested head;
- content addressing of supplied offline dependency artifacts;
- doctor integration that persists `mace_runtime_freeze` evidence and hard-fails a requested CuEq campaign when the frozen accelerator capability is incomplete; and
- a pure fail-closed doctor backend guard that never rewrites the configured backend.

Authenticated evidence from the supplied development artifacts:

- dependency archive SHA-256: `888d545a512396697c8583d69bc9ed33110914675f466a4cbcafc3e1e1407171`;
- MH-1 checkpoint SHA-256: \nolinkurl{ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde}; requested `omat_pbe` e3nn calculator load: **PASS**;
- MPA-0-medium checkpoint SHA-256: `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`; requested `default` e3nn calculator load: **PASS**;
- all eight locked MACE `0.3.16` source hashes: **PASS** against the supplied source tree;
- CuEq core/Torch/ops availability in the supplied archive/runtime: **ABSENT**;
- OpenEquivariance availability in the supplied archive/runtime: **ABSENT**;
- e3nn backend capability: **PASS**;
- CuEq backend capability: **FAIL CLOSED** with explicit missing-CuEq/OEQ reasons and no fallback mutation.

The machine-readable evidence is retained as `audits/analysis/mlff_mh1_dep0_runtime_freeze_evidence.json`. Its record digest is `00a98ff9d1ea5ac94af91a8581cb7118d599df4d3d42c522271c2da44b36a862` for the execution environment used to produce this gate evidence. That evidence environment is CPU-only and is not itself the later CUDA/CuEq production environment; the record intentionally preserves that distinction rather than claiming accelerator qualification.

Focused verification:

- DEP0 focused suite: **6 passed** including both supplied real checkpoints;
- campaign/runtime/CuEq integration regression: **62 passed, 3 environment-dependent skips, 2 deselected**;
- a broader historical MLFF sweep reached **159 passing tests** before stopping on pre-existing stale specification tests that still assert the historical `0.20.140a0` version/default text. Those failures are unrelated to DEP0 and are not repaired by this gate because doing so would change historical specification evidence.

No generated campaign default, foundation identity, replay semantics, DATA6 selection behavior, DATA8 training policy, stopping rule, checkpoint ranking, or deployment behavior is changed by DEP0.

## Gate MH1-BASE0 - locked MPA-0 regression baseline

Capture the existing `0.20.177a0` MPA-0 behavior before identity/schema changes. The purpose is to distinguish intended generalization from accidental changes to the completed scientific workflow.

### MH1-BASE0 code/evidence changes

Primarily tests/fixtures. Establish authenticated baseline evidence for explicit MPA-0/e3nn and MPA-0/CuEq configurations across:

- checkpoint/foundation identity;
- DATA6 descriptors and predictions;
- DATA7 fitted metric and selection;
- replay preparation;
- DATA8 training configuration;
- checkpoint evaluation policy;
- production materialization and target-head export; and
- deployment verification.

### MH1-BASE0 acceptance gate

An explicitly configured legacy MPA-0 campaign reproduces pre-revision behavior except for separately versioned identity normalization. No target-selection, training-budget, LR, checkpoint-ranking, physical-verification, or locked-test rule changes in this revision.

### MH1-BASE0 implementation record - 2026-08-14

**Status: complete.** BASE0 adds regression evidence only; it does not alter campaign execution or scientific policy. The gate freezes the pre-generalization MPA-0 contracts in two complementary forms:

- `tests/fixtures/mlff_mh1_base0_legacy_mpa0.json` is an immutable legacy-payload fixture (SHA256 `c22d60aa95d3e8cdca3ab688c9333d9ea026f91db4a5a7c856f9a8c4f98a38a2`). It preserves the exact `0.20.177a0` serialized MPA-0 foundation/checkpoint identities, explicit e3nn and CuEq acceleration policies, checkpoint-evaluation policies, checkpoint-bound pseudolabel replay plan, FP32 deployment-verification policy, and target-head export identity. Later schema gates must normalize these payloads rather than silently reinterpret or discard them.
- `audits/analysis/mlff_mh1_base0_mpa0_regression_evidence.json` is the machine-readable baseline evidence (SHA256 `9dc55c995899a27de4b4e9645fe7e1d202faf02e4ce5ac8d0f6fe3b2f92db079`). It records the supplied MPA-0 checkpoint SHA256 `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`, current schema names, explicit generated campaign-template semantics, deterministic synthetic DATA6/DATA7 fingerprints, DATA8 e3nn/CuEq training-config semantics, production-materialization identity, and a real stock-MACE e3nn numerical reference.

The deterministic synthetic pipeline freezes the current pre-MH1 behavior at:

- DATA6 bundle `5efb745fd2f317a40053962b822300b36eee898f10b633d8ec7c952a20ce24c9`;
- DATA6 descriptor manifest `a07b8fd183bde4aefeba3a0a1a7b0988af10377375a380795788efde9638de28`;
- DATA6 prediction manifest `15fc7556dd9f90ac08ec1ca3e917c8d61b1f73cb5f1a017dadef70ccdb3c194e`;
- final DATA7 fitted metric `5aa8c5f7559418c45ed0ff6319053f540bbda2e51971919c05f8673ee985c8a6`, with transformed shape `36 x 77`;
- final DATA7 nested selection `f56a7c901e2b8d0434b4b6816c24ba054d1b13814f6051a4aac03f92b60c117e` at sizes `8, 16, 24`; and
- representative legacy production-materialization plan `fc32af306e0956829962683adcd6122d2b6309e0b2577743677feed828e142c5`.

The DATA8 baseline explicitly proves that the legacy MPA-0 source head is `default` in both paths; e3nn serializes `enable_cueq=false`, whereas the CuEq path serializes `enable_cueq=true`, `only_cueq=false`, with the same `target_head`/`pt_head` multi-head replay topology and explicit replay train/validation files. CuEq **numerical** evidence is intentionally not invented here because the supplied DEP0 runtime lacks CuEq/OEQ; BASE0 freezes its configuration/protocol behavior and leaves numerical accelerator qualification to `MH1-ACCEL1`.

The real supplied MPA-0 checkpoint is also frozen through stock MACE 0.3.16/e3nn on one deterministic six-species periodic structure. The reference descriptor width is `256` invariant features per atom. FP32 gives energy `-13.267881393432617 eV` and force-component RMS `0.8111847639083862 eV/A`; FP64 gives `-13.267878461628188 eV` and `0.8111845825720752 eV/A`. Exact descriptor-byte hashes are recorded in the evidence file and checked by the slow integration test.

BASE0 also captures two historical semantics that later normalization must handle deliberately:

1. generated legacy campaign TOMLs leave `evaluation.replay_baseline_head = ""`, while constructing a bare `CheckpointEvaluationPolicy()` yields in-memory `replay_baseline_head_name="pt_head"`; and
2. the representative historical production plan serializes as `mdstats.production-materialization-plan.v5` even though the newest recognized plan schema constant is v6, because the older policy surface intentionally preserves its prior digest identity.

Verification:

- BASE0 focused non-slow suite: **3 passed**;
- BASE0 real MPA-0/e3nn numerical test: **1 passed** in both FP32 and FP64 branches;
- surrounding DATA6/DATA7/DATA8/materialization/evaluation/deploy/CuEq-policy/legacy-schema regression: **75 passed, 1 slow test deselected**.

No production module was changed by BASE0. The only source-package additions are the authenticated legacy fixture, regression test, machine-readable evidence, and this documentation record.

## Gate MH1-ID1 - generalized foundation contract and checkpoint inspection

Introduce the canonical generalized MACE foundation module and eliminate filename/model-name authority.

### MH1-ID1 concrete code changes

Primary files:

- new `mdstats/training_data/foundation.py` (or the equivalent canonical package location);
- `mdstats/training_data/protocol.py`;
- public `__init__.py` exports;
- serializers/schema compatibility helpers; and
- focused foundation identity tests.

Implement at least:

- `MaceFoundationFamily` with `mace_mh_1`, `mace_mpa_0`, and a safe custom/general MACE path;
- `MaceFoundationSpec`;
- CPU/lightweight `MaceFoundationInspection`;
- `FoundationPotentialIdentity`;
- `FoundationInferenceIdentity` scaffolding;
- exact available-head discovery;
- model-family/checkpoint compatibility validation;
- actual element-table inspection;
- serialized architecture signature generation; and
- legacy singleton normalization.

`protocol.FoundationCheckpointIdentity` advances from its current schema to a canonical head-qualified schema backed by this shared object rather than independent logic.

### MH1-ID1 acceptance gate

1. the same MH-1 bytes under `omat_pbe` and `omol` produce different scientific foundation identities;
2. MPA-0 resolves its actual singleton head without filename assumptions;
3. omitted/invalid MH-1 heads fail before MACE calculator construction;
4. a config declaring `mace_mh_1` while pointing at the supplied MPA-0 checkpoint fails, and vice versa;
5. requested species must be a subset of the checkpoint's actual supported atomic numbers; and
6. legacy head-blind artifacts normalize only for authenticated single-head foundations.

### MH1-ID1 implementation record - 2026-08-14

MH1-ID1 is implemented against the BASE0 source snapshot. The gate introduces `mdstats/training_data/foundation.py` as the canonical generalized-MACE boundary and advances new foundation-checkpoint identities to `mdstats.foundation-checkpoint-identity.v3`. The new public contracts are `MaceFoundationFamily`, `MaceFoundationSpec`, `MaceFoundationInspection`, `FoundationPotentialIdentity`, `FoundationInferenceIdentity`, and `inspect_mace_foundation`. `protocol.FoundationCheckpointIdentity` is now the backward-compatible public alias of the shared `FoundationPotentialIdentity` implementation rather than a second independent identity class.

The strict generalized path is `MaceFoundationSpec.resolve_file()`: it hashes and CPU-loads the actual serialized checkpoint before calculator construction, records exact available heads, the actual model element table, atomic-E0 tensor shape, interaction/product/readout structure, selected architecture flags, and a state-dictionary shape digest, and derives a deterministic serialized-architecture signature. Family compatibility is structural rather than filename based. `mace_mpa_0` requires the authenticated singleton `default`/density-interaction structure; `mace_mh_1` requires the authenticated multi-head nonlinear/agnostic-product structure including `omat_pbe`; `mace_custom` remains the safe general MACE escape hatch while retaining exact head/species checks. Multi-head models require an explicit requested head and invalid heads fail before `MACECalculator` can apply any fallback. Requested atomic numbers must be a subset of the checkpoint's actual supported element table.

The supplied locked checkpoints produce the following inspection evidence:

- MH-1 SHA256 \nolinkurl{ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde}; six heads in checkpoint order `matpes_r2scan`, `mp_pbe_refit_add`, `spice_wB97M`, `oc20_usemppbe`, `omol`, `omat_pbe`; 89 supported elements; atomic-E0 shape `(6, 89)`; `edge_irreps=128x0e+128x1o`; `use_agnostic_product=True`; serialized architecture signature `c6fe21484b986728373c0853dcaf0339fb4b6d449193c3dea1529149ee41050d`.
- MPA-0-medium SHA256 `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`; singleton head `default`; the same 89-element table; atomic-E0 shape `(89,)`; density interaction blocks; serialized architecture signature `c06e20329de9805c382d684dca0efab1ac4da8c58f8b51b67209bfaff2c7d6bf`.

For the exact same MH-1 checkpoint bytes, the canonical `omat_pbe` and `omol` scientific identities are distinct (`06bf87891d6addebd3ea300fa23fd6401f0b74897f5676394e99507d03c8fc59` versus `77f92d39608f9875aae1dc4ba589c74ea6944fe9c88f5883a5e5867bf6067a0d`). The canonical MPA-0/default identity is `e6f6001827be216a9a8e8cb1829f2e2b996c846492f6f3975b6e6759064880dd`. Machine-readable gate evidence is stored at `audits/analysis/mlff_mh1_id1_foundation_evidence.json`.

Legacy migration is deliberately digest preserving. A deserialized v2 foundation record retains v2 serialization semantics so any historical parent artifact that embedded it can still verify its original digest; the object separately exposes `canonical_content_digest` and may be explicitly canonicalized after inspecting the real checkpoint. A simulated head-blind v1 record is accepted only when the referenced bytes still match the authenticated SHA and inspection proves a true singleton checkpoint. The locked MPA-0 model passes that migration; the locked MH-1 model fails it as ambiguous. Inspection/migration state is evidence metadata and is not part of the scientific potential digest, so a legacy-authenticated singleton canonicalizes to the same scientific identity as a fresh inspection.

`FoundationInferenceIdentity.v1` is introduced only as execution-identity scaffolding in this gate. It layers dtype, requested backend, resolved-kernel label, MACE version, and adapter version over the scientific `FoundationPotentialIdentity` digest. Accelerator realization and DATA6 cache authority remain deferred to MH1-ACCEL1/MH1-DATA6-1. The existing lightweight `FoundationCheckpointIdentity.from_file()` constructor remains available temporarily for historical/dummy-file callers; generated generalized campaigns do not gain authority from it. MH1-CONFIG1 is responsible for switching generated campaigns to the strict inspected `MaceFoundationSpec.resolve_file()` path.

`data8_bundle._stage_foundation_checkpoint()` now relocates an identity with `dataclasses.replace()` rather than reconstructing it from the historical four fields, ensuring architecture/head-table evidence cannot be discarded merely by staging. Public exports in `mdstats.training_data` and `mdstats` expose the generalized contracts.

Focused real/synthetic ID1 tests pass 5/5. Surrounding legacy-schema, DATA8/materialization, precision/TRAIN2, campaign-control, evaluation/PES, and checkpoint-materialization regressions pass 114 tests with four environment-dependent skips in the executed non-slow subsets. No generated campaign default, DATA6 `ModelCheckpointIdentity`, replay provenance, stopping/LR policy, evaluation authority, or deployment default is changed by ID1.

## Gate MH1-CONFIG1 - generated MH-1 defaults and canonical configuration

Replace MPA-oriented generated configuration semantics with a canonical `[foundation]` section while retaining read compatibility for historical TOML.

### MH1-CONFIG1 concrete code changes

Primary file: `campaign_cli.py`, plus configuration schema/tests/user guide where generated examples are normative.

New generated campaign defaults:

```toml
[campaign]
id = "lta-mh1-omat-pbe-finetune"

[foundation]
family = "mace_mh_1"
head = "omat_pbe"

[paths]
foundation_model = "/path/to/mace-mh-1.model"

[acceleration]
backend = "cueq"
only_cueq = false
require_available = true
```

`init` may expose explicit `--foundation-family`, `--foundation-head`, and `--backend` overrides, but the common path requires none. It writes `cueq` as policy even when initialization occurs on a host without CuEq. Doctor is responsible for runtime qualification.

The old `model.foundation_name` may remain a migrated human-readable label, but it cannot identify the physical foundation. Existing independent controls such as replay-baseline or PES-foundation head names must normalize to the canonical `[foundation].head` for new campaigns rather than remain separate scientific selectors.

### MH1-CONFIG1 acceptance gate

1. a fresh campaign visibly generates `MACE-MH-1`, `omat_pbe`, and `cueq` defaults;
2. an old MPA-0 campaign remains restartable without automatic TOML rewriting;
3. generated configuration contains one canonical source-foundation head; and
4. changing the foundation/head/backend changes the appropriate frozen identity before preparation.

### MH1-CONFIG1 implementation record - 2026-08-14

MH1-CONFIG1 is implemented on the `0.20.177a0` development line. It changes the generated campaign configuration only; calculator construction, named-head E0 access, DATA6 `ModelCheckpointIdentity`, replay generator lineage, DATA8 foundation extraction, and evaluation/deployment source-head authority remain deferred to their later gates.

`campaign_cli._config_template()` is now parameterized by foundation family/head and generates `mace_mh_1` + `omat_pbe` + `cueq` by default. `command_init` no longer probes the host to choose the acceleration backend: it writes the requested policy explicitly, with `cueq` as the default even on hosts where CuEq is absent. `--foundation-family`, `--foundation-head`, and `--backend` provide explicit overrides; `mace_mpa_0` + `default` + `e3nn` remains an intentionally supported generated legacy/reference configuration. The shipped `campaign.toml.example` now reflects the generalized default and points to `/path/to/mace-mh-1.model`.

The new canonical TOML namespace is `[foundation]` with `family`, `head`, and a non-authoritative human-readable `label`. `[model].foundation_name` remains only as a compatibility/display label. Existing pre-CONFIG1 MPA-0 TOML files are normalized **in memory only** to `mace_mpa_0/default`; mdstats does not rewrite their TOML. Unknown head-blind legacy foundations are not guessed. Explicit generalized `[foundation]` families are normalized through the ID1 family parser, and missing/invalid family/head declarations fail during config loading.

New generalized templates no longer emit the historical independent `evaluation.replay_baseline_head` or `verification.pes_foundation_head` selectors. Their source head is the canonical `[foundation].head`. If a generalized config manually retains either legacy selector with a conflicting non-empty value, config loading fails. Explicit legacy MPA-0 templates retain the historical blank selectors so BASE0 remains a faithful migration fixture; final downstream evaluation/PES authority migration remains MH1-EVAL1.

A versioned pre-preparation `mdstats.mlff-foundation-config-contract.v1` digest now covers canonical family, source head, requested backend, `only_cueq`, and `require_available`. `doctor` records that contract in campaign metadata before preparation. The locked default contract digest is `769979ea00fa7be89a62fc845fcca73a1a276329a6b6e993279e4eaab2273f22`; changing to MH-1/`omol`, MH-1/e3nn, or MPA-0/default/e3nn yields distinct digests. This contract is configuration evidence only and does **not** replace the inspected scientific foundation identity introduced by ID1 or the execution identity to be bound by INF1/ACCEL1.

Focused CONFIG1/default/migration tests pass 11 tests; the CONFIG1 plus BASE0-template compatibility slice passes 12 tests with three unrelated tests deselected. The surrounding campaign/configuration/DATA8/materialization/evaluation regression executed for the gate passes 162 tests with one environment-dependent skip. Machine-readable evidence is stored at `audits/analysis/mlff_mh1_config1_configuration_evidence.json` with digest `45f8e3b4248c0a6ba6cc36bd7a0cdb62e7cb181f9030ada6f51a89a8bab46ecd`.

## Gate MH1-INF1 - head-aware inference, E0 access, and DATA6 root identity

Eliminate every remaining source-foundation inference path that relies on an implicit/default/first head.

### MH1-INF1 concrete code changes

Primary files:

- `campaign_cli.py` (`_provider`, `_model_checkpoint_identity`, `_extract_foundation_e0`, doctor helpers);
- `model_features.py`;
- `acceleration.py` construction helpers; and
- any critical-precision/foundation-audit path that still constructs a multi-head foundation calculator.

Required changes:

- resolve the canonical foundation identity before calculator construction;
- pass `head=resolved_head` explicitly to every multi-head foundation `MACECalculator`;
- remove integer/default `head_index=0` E0 authority;
- resolve MH-1 atomic E0 rows by exact head name and validate head/E0 table consistency;
- advance DATA6-side `ModelCheckpointIdentity` to include/reference the canonical foundation potential identity and its execution identity;
- separate model-supported and campaign-requested atomic numbers; and
- remove cache reuse rules that reject explicit heads simply because old DATA6 evidence was head-blind.

### MH1-INF1 acceptance gate

1. all foundation energy/force/stress/descriptor/E0 paths identify the exact resolved head;
2. DATA6 identity differs across MH-1 heads even with an identical checkpoint SHA;
3. cached DATA6 foundation predictions are reusable only under an exact scientific/execution identity match; and
4. an invalid source head cannot reach MACE's internal fallback logic.

### MH1-INF1 implementation record - 2026-08-14

MH1-INF1 is implemented on the CONFIG1 source snapshot. New source-foundation inference resolves `MaceFoundationSpec` against the actual checkpoint before constructing `MACECalculator`, and every campaign foundation calculator is created with the resolved canonical head explicitly. Doctor's CuEq model smoke now receives the canonical source head as well. Foundation PES and foundation-baseline evaluation paths likewise use canonical `[foundation].head` rather than the historical blank replay/PES aliases; candidate-model head semantics remain unchanged.

DATA6 `ModelCheckpointIdentity` advances from `mdstats.model-checkpoint-identity.v1` to `v2`. A foundation-backed v2 identity binds the canonical `FoundationPotentialIdentity` digest, `FoundationInferenceIdentity` digest, exact foundation head, actual checkpoint-supported atomic-number table, campaign-requested atomic-number subset, dtype/device, and acceleration-policy metadata. Generic/candidate model providers may remain unbound. Historical v1 payloads preserve their exact v1 serialization and content digest when deserialized so BASE0 parent artifacts remain readable. A foundation-bound provider is immutable with respect to source head: `set_head()` may reassert the frozen head but rejects switching to another head.

The former DATA6 `supported_atomic_numbers` ambiguity is removed for new source-foundation identities. `model_supported_atomic_numbers` records the checkpoint element table while `requested_atomic_numbers` records the campaign profile; the historical field remains a compatibility alias. For the locked MH-1 and MPA-0 checkpoints the actual model support table contains 89 atomic numbers, while the LTA campaign requests only its configured chemistry.

Foundation E0 extraction no longer accepts or defaults an integer `head_index`. It authenticates the checkpoint atomic-number/head tables against the resolved scientific identity, checks the E0 tensor rank and row count, indexes a multi-head E0 table by the exact named head, and fails on any table/head inconsistency. On the locked MH-1 checkpoint, `omat_pbe` and `omol` produce distinct named-head E0 tables as expected.

DATA6 foundation prediction-cache reuse is now asymmetric by schema. New v2 foundation-bound DATA6 predictions are reusable when the explicit evaluation head equals the frozen DATA6 foundation head and checkpoint/dtype/device/acceleration-policy identity also matches. Historical head-blind v1 DATA6 evidence remains restricted to the old implicit-singleton path and is never assigned a head by guesswork. Replay pseudolabel generator lineage is intentionally not migrated in this gate; that remains MH1-LINEAGE1.

Focused INF1 tests pass 6/6, including real CPU/e3nn loads of the uploaded MH-1 `omat_pbe` and MPA-0 `default` checkpoints, named-head E0 extraction, distinct MH-1 head identities, invalid-head rejection before calculator construction, bound-provider head immutability, explicit-head DATA6 cache reuse, and v1 digest-preserving migration. The surrounding BASE0/CONFIG1/ID1, DATA6, CuEq-policy, evaluation/PES, DATA8/materialization, campaign CLI, and restart/performance slices executed for this gate pass 132 tests with one environment-dependent skip. Machine-readable evidence is stored at `audits/analysis/mlff_mh1_inf1_head_aware_inference_evidence.json` with digest `5d6996df30285cdf6a632274407d14a57d937e0bb6433c740411d60c94ff00cd`.

## Gate MH1-EXTRACT1 - checkpoint-faithful MH-1 selected-head extraction

Resolve the known MACE 0.3.16 MH-1 reconstruction incompatibility before production DATA8 training depends on selected-head extraction.

### MH1-EXTRACT1 concrete code changes

Primary files:

- `foundation.py` architecture inspection/reconstruction helpers;
- `mace_compatibility.py`;
- `mace_realization.py`; and
- a narrowly scoped compatibility module if required.

The preferred order is:

1. invoke stock MACE selected-head extraction and record success/failure;
2. on the exact affected MACE/version/architecture conditions only, reconstruct the missing architecture information from the loaded serialized model;
3. create a derived selected-head model without altering the source checkpoint or installed MACE package;
4. record source checkpoint SHA, source head, serialized architecture digest, compatibility-shim version, derived checkpoint SHA, and reconstruction evidence; and
5. prove numerical parity against the original multi-head model explicitly evaluated at `omat_pbe`.

The shim must not become a permanent replacement for upstream MACE. A later tagged MACE whose stock extraction passes must bypass the compatibility shim and pass a self-disablement regression test.

### MH1-EXTRACT1 acceptance gate

A selected `omat_pbe` foundation model is eligible for DATA8 only when:

- state-dictionary shapes are architecture-consistent;
- source and derived energy, forces, stress, atomic E0 semantics, and DATA6 descriptors satisfy parity policy on the deterministic qualification set;
- the derived artifact has immutable source/shim provenance; and
- the original MH-1 checkpoint remains byte-identical.

### MH1-EXTRACT1 implementation record (2026-08-14)

MH1-EXTRACT1 is implemented on the INF1 source snapshot. The implementation adds a dedicated `mace_head_extraction.py` compatibility boundary rather than modifying the installed MACE package or the source foundation checkpoint. `MaceSelectedHeadCompatibilityPolicy` is version-guarded to `mace-torch==0.3.16`; stock `mace.tools.scripts_utils.remove_pt_head()` is always attempted first, and the architecture shim self-disables whenever stock extraction succeeds. If stock extraction fails, mdstats authorizes one correction only when the loaded checkpoint proves the exact affected MH-1 architecture: `ScaleShiftMACE`, first interaction `RealAgnosticResidualNonLinearInteractionBlock`, missing top-level `use_edge_irreps_first`, non-null model edge irreps, and serialized first-interaction/`linear_up` edge projection matching the scalar component of the model edge representation.

The locked MH-1 checkpoint proves that condition. Its model edge representation is `128x0e+128x1o`, while the already-serialized first interaction and `linear_up` projection are `128x0e`; the absent top-level metadata caused MACE 0.3.16 to reconstruct the first interaction at 512 channels and fail with the known 4x state-dictionary shape mismatch. mdstats temporarily restores `use_edge_irreps_first=True` only on the in-memory source object during reconstruction, then removes the temporary attribute. The original checkpoint bytes remain unchanged. The derived single-head checkpoint carries the serialized `omat_pbe` head and, unlike the stock helper under an ambient float32 Torch default, preserves the source model dtype. The source and derived models are both float64. This dtype guard is part of the compatibility contract because constructing the derived module in float32 loses source precision before `load_state_dict()` and cannot be repaired afterward by casting back to float64.

Four immutable evidence contracts are introduced: `MaceSelectedHeadExtractionRecord`, `MaceSelectedHeadParityPolicy`, `MaceSelectedHeadParityRecord`, and `MaceSelectedHeadQualificationRecord`. The extraction record binds the canonical source-potential digest, source checkpoint SHA, source architecture signature, exact source head, MACE version, compatibility-policy digest, authenticated stock-failure evidence, shim evidence digest, derived checkpoint SHA/architecture signature, source/derived dtype, and source-byte-preservation state. The qualification record becomes training-qualified only when source multi-head inference at the explicit source head and the derived singleton model pass energy, force, stress, atomic-E0, and invariant-descriptor parity.

The real locked `mace-mh-1.model` / `omat_pbe` qualification uses three deterministic structures spanning NaCl, SiO2, and Al-Na-Si-O chemistry (12 atoms total) under CPU/e3nn float64 inference. Stock MACE 0.3.16 extraction fails as expected, the narrow edge-projection shim is applied, and the derived checkpoint SHA is \nolinkurl{7b6f3cce6d2086164082f1cb5739098de2db990d6a49f0d60e66a3a0f1ae545e}. Source-vs-derived maximum differences are `3.552713678800501e-15 eV` in total energy, `4.551914400963142e-15 eV/A` in forces, `4.9439619065339e-17 eV/A^3` in stress, `2.4868995751603507e-14` in the 1024-wide invariant descriptor, and exactly `0.0 eV` in atomic E0s. The source checkpoint remains SHA \nolinkurl{ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde} before and after extraction. Machine-readable gate evidence is stored at \nolinkurl{audits/analysis/mlff_mh1_extract1_selected_head_evidence.json} with evidence digest \nolinkurl{46d546f71abcd5a0e4dfa09a30fb4df62288248cceef90125c088b4f62055081}.

Focused EXTRACT1 unit tests pass the stock-success self-disablement path, refusal to patch failures outside the exact version/architecture guard, policy serialization, and the real MH-1 extraction/parity path. Relevant compatibility/DATA8/checkpoint-materialization/production-materialization regression slices remain green. The derived real checkpoint is an external gate artifact and is deliberately not bundled into the mdstats source package; later DATA8 lineage may bind its authenticated SHA/qualification record without redistributing foundation-model assets.

## Gate MH1-ACCEL1 - e3nn reference and CuEq realization qualification

Develop and test e3nn and CuEq as complete backend paths, with CuEq generated by default and e3nn as the numerical reference/fallback selected only by explicit configuration.

### MH1-ACCEL1 concrete code changes

Primary files:

- `acceleration.py`;
- `campaign_cli.py` doctor/preflight/reporting;
- provider construction used by DATA6, training, evaluation, and verification; and
- acceleration/parity tests.

Advance the existing acceleration probe into a paired `AccelerationRealizationRecord`/capability contract that records:

- requested backend (`cueq` or `e3nn`);
- resolved **inference** mode (`e3nn`, `cueq_pure`, or `cueq_oeq_hybrid`);
- separately resolved **training** mode (`e3nn` or `cueq_pure` under MACE 0.3.16);
- CuEq/OEQ package/runtime versions;
- dtype/device;
- foundation inference identity; and
- inference/training parity statistics.

MACE 0.3.16 supports CuEq+OpenEquivariance hybrid conversion in `MACECalculator`, but `run_train.py` explicitly disables OEQ when both CuEq and OEQ are requested and trains with pure CuEq. Therefore hybrid is an inference realization only in the pinned runtime. A CuEq production campaign may prefer a qualified `cueq_oeq_hybrid` inference realization for MH-1, but **pure CuEq must independently pass parity because it is the only CuEq training realization authorized by MACE 0.3.16**. Hybrid parity may never rescue failed pure-CuEq training parity.

Use a deterministic qualification corpus spanning representative LTA compositions, thermal distortions, strain, and mobile-ion/high-force environments. Compare every CuEq realization with e3nn for energy per atom, forces, stress, invariant descriptors, and deterministic FPS selection stability.

### MH1-ACCEL1 acceptance gate

1. MH-1/`omat_pbe`/e3nn passes the complete foundation inference/descriptor smoke path in both supported model dtypes;
2. MH-1/`omat_pbe`/CuEq freezes an inference realization (`cueq_pure` or `cueq_oeq_hybrid`) **and** independently qualifies `cueq_pure` for training;
3. MPA-0/e3nn and MPA-0/CuEq retain regression qualification;
4. energy-per-atom, force, stress, invariant-descriptor, and deterministic-FPS parity pass against e3nn for each authorizing CuEq realization;
5. the resolved inference realization cannot change between prepare/evaluate/verify without identity mismatch, and DATA8 cannot change the independently frozen training realization; and
6. failed/missing CuEq qualification fails doctor instead of silently selecting e3nn.

### MH1-ACCEL1 implementation record - 2026-08-14

The ACCEL1 implementation is complete on the EXTRACT1 source snapshot. `acceleration.py` now separates the user-facing backend (`cueq` or `e3nn`) from the exact runtime implementation through `MaceAccelerationKernelMode`, `MaceAccelerationParityPolicy`, `MaceAccelerationParityRecord`, and `AccelerationRealizationRecord`. The realization binds the foundation-inference identity, dtype/device, MACE/CuEq/OEQ versions, an inference kernel mode, and a separately frozen training kernel mode. For e3nn both modes are `e3nn`; for an authorizing CuEq campaign under MACE 0.3.16 the training mode is always `cueq_pure`, while inference may be `cueq_pure` or `cueq_oeq_hybrid`.

The phase split is required by the pinned upstream implementation rather than by mdstats policy. The locked MACE 0.3.16 `mace/cli/run_train.py` (SHA-256 `4f219fce454279b54cb7a10af30e8e8508cb7b83b3ffa6981ed89dbe7dc8de8b`) explicitly detects simultaneous `enable_cueq`/`enable_oeq`, warns that CuEq will be used for training, and sets `enable_oeq=False`; `MACECalculator` (SHA-256 `97b17cef8d5880071068d1a05a97f1d432ffc57db00d23ba86c2c3049114a8ad`) independently exposes both flags and the hybrid inference conversion. `MaceOptimizerPolicy.v6` therefore binds only `e3nn` or `cueq_pure` as a training realization and rejects `cueq_oeq_hybrid` before DATA8 serialization. `CheckpointEvaluationPolicy.v6` binds the inference realization and may use the hybrid mode. Legacy optimizer/evaluation schemas remain readable.

Doctor now builds a deterministic local qualification corpus, resolves the exact foundation/head, evaluates e3nn as the canonical reference, and—for a CuEq request—tests pure CuEq and, when available, the CuEq+OEQ hybrid independently. Parity covers energy **per atom**, forces, stress, invariant descriptors, and a deterministic FPS-selection fingerprint. The default policy uses `rtol=1e-5, atol=1e-6` for FP32 and `rtol=1e-10, atol=1e-12` for FP64. MH-1 prefers a parity-qualified hybrid inference realization when available, but pure-CuEq parity remains mandatory for training authorization; a passing hybrid cannot rescue a failed pure-CuEq result. No path silently rewrites the requested backend to e3nn.

The frozen realization is persisted by doctor and enters the DATA6 foundation-inference identity, evaluation policy/cache identity, PES/NVE calculator identity, and DATA8 optimizer identity. New canonical `[foundation]` campaigns require a qualified realization before preparation/evaluation/verification. Pre-MH1 campaigns that never persisted a realization retain their historical acceleration-policy execution semantics and are not retroactively assigned a fabricated realization.

Real e3nn qualification passes on both locked production checkpoints in both supported dtypes: MH-1/`omat_pbe` and MPA-0/`default` each pass FP32 and FP64 energy/force/stress/descriptor evaluation on the deterministic three-structure corpus. The current supplied development runtime exposes the MACE 0.3.16 CuEq and OEQ constructor interfaces but contains neither the CuEquivariance packages nor OpenEquivariance and has no authorizing CUDA accelerator runtime. Consequently **real CuEq numerical certification is environment-blocked, not passed**. The code path is fail-closed: the runtime probe records CuEq/OEQ as unavailable, a CuEq realization remains unqualified, and a default CuEq campaign cannot proceed to preparation. This is intentionally not replaced by e3nn. Real CuEq acceptance items 2--4 remain pending until the accelerator runtime is supplied.

Focused ACCEL1 tests cover realization serialization/phase separation, hybrid-preferred inference with pure-CuEq training, refusal to let hybrid rescue failed pure-CuEq parity, missing-CuEq fail-closed behavior, optimizer rejection of hybrid training, MACE OEQ-constructor discovery, inference-policy binding, and real e3nn qualification. The real-model integration test passes all four model/dtype combinations. Surrounding DATA8/materialization/legacy-schema/evaluation/cache/NVE/PES/deployment slices remain green after adding legacy no-realization normalization. Machine-readable evidence is stored at `audits/analysis/mlff_mh1_accel1_acceleration_evidence.json` with content digest `fe96fe97fde0728f4db2ad374921d151fd9eab8fad5238ab48522cb3d36451cd`.

## Gate MH1-DATA6-1 - MH-1 descriptor adapter, batching, and DATA6/DATA7 compatibility

Qualify the custom native-batched DATA6 descriptor path against MH-1's nonlinear architecture and larger feature dimensions without creating a separate MH-1-specific scientific metric.

### MH1-DATA6-1 concrete code changes

Primary files:

- `model_features.py`;
- DATA6 model-sweep/cache code;
- DATA7 metric/bundle compatibility code; and
- campaign batch-size planning.

Refactor duplicated native descriptor reconstruction into one internal architecture-aware MACE descriptor adapter used by both descriptor-only and prediction+descriptor batch paths. Add a versioned `MaceDescriptorSignature` including:

- model/architecture signature;
- selected foundation head;
- per-layer raw dimensions;
- invariant/full per-atom descriptor dimensions;
- returned structure-level dimensions;
- invariants-only/full policy; and
- descriptor adapter/policy versions.

For the supplied fixtures, the observed 1024/2560 MH-1 versus 256/640 MPA-0 per-atom dimensions become qualification expectations, not universal hard-coded constants.

Replace the generic MPA-era initial inference-memory estimate with architecture-aware runtime calibration. Doctor/preflight should probe increasing real batch sizes, record peak allocation/descriptor footprint where available, choose a conservative initial DATA6 batch, and retain existing OOM bisection as a safety fallback.

DATA7 continues to fit its generic dimension-adaptive PCA/feature metric from the exact DATA6 descriptor identity. No separate `MH1 metric` or model-specific FPS weighting is introduced.

### MH1-DATA6-1 acceptance gate

1. official/single-structure MACE descriptor output and mdstats native batching agree for both supplied foundations and both qualified backends;
2. descriptor dimensions/signatures are explicit cache identity;
3. changing foundation/head/backend/descriptor adapter invalidates only the appropriate DATA6/DATA7 derived evidence;
4. MH-1 batching is bounded by measured/model-aware capacity rather than MPA-only constants; and
5. CuEq/e3nn descriptor differences do not materially alter deterministic DATA6 selection on the qualification pool under the declared selection-stability policy.

### MH1-DATA6-1 implementation record - 2026-08-14

**Implementation status: complete for descriptor architecture, e3nn qualification, cache lineage, and model-aware batching; real CuEq descriptor/selection parity remains environment-blocked.** No CuEq success is inferred from the e3nn result, and the requested CuEq campaign remains fail-closed until an authorizing CuEq/OEQ + CUDA runtime is supplied.

`model_features.py` now owns a single internal `_MaceDescriptorAdapter` used by both descriptor-only and combined prediction+descriptor native batch paths. The adapter derives descriptor structure from the loaded model rather than from MPA-0 constants and publishes `MaceDescriptorSignature.v1`. The signature binds the model/architecture signature, selected source head, per-layer raw dimensions, invariant/full per-atom dimensions, returned dimensions, invariant/full policy, and adapter/policy versions. The descriptor adapter/policy advance to `mdstats.mlff-data6.mace-calculator.2026-08.v2` and `mdstats.mlff-data6.mace-descriptor.2026-08.v2`.

`MaceDescriptorManifest` advances to `mdstats.mace-descriptor-manifest.v2` and `Data6ModelSweepPlan` advances to `mdstats.data6-model-sweep-plan.v2` whenever a real descriptor signature exists. Historical v1 plans/manifests remain readable and preserve their historical digest; lightweight/fake-provider paths without an authenticated native descriptor signature continue to serialize as v1 rather than fabricating v2 authority. The model-sweep lineage-only reuse rule now also requires the descriptor-signature digest to match, so foundation/head/backend/adapter changes cannot incorrectly reuse descriptor evidence while unrelated prediction-side evidence remains independently reusable under its own identity. DATA7 remains dimension-adaptive and consumes the exact DATA6 descriptor lineage; no MH-1-specific PCA/FPS metric was introduced.

The real e3nn acceptance test compares the official MACE single-structure descriptor API with mdstats native batching for both invariant and full descriptor policies on both locked production checkpoints. The uploaded MH-1/`omat_pbe` checkpoint measures **1024 invariant / 2560 full features per atom**, while MPA-0/`default` measures **256 / 640**. The observed maximum official-vs-native absolute difference is **0.0** for both models and both policies in the locked test corpus. These dimensions are recorded qualification evidence, not hard-coded family constants.

`MaceBatchCapacityCalibration.v1` adds model-aware batch-capacity evidence. `doctor` performs the authoritative probe whenever the requested acceleration realization is qualified, persists the calibration, and `prepare` reuses it only when descriptor signature, device, requested maximum batch, and device-budget authority still match. Otherwise `prepare` recalibrates. CUDA probes increasing real batch sizes and records peak-device/graph/descriptor footprint where available; CPU deliberately probes one structure because DATA6 batch throughput optimization is GPU-oriented. Existing OOM bisection remains the final safety fallback. On the current CPU reference environment, the locked MH-1 sample records 16,384 descriptor bytes and 3,987 graph bytes per two-atom structure; MPA-0 records its independently measured footprint. These CPU numbers are evidence only and are not used as universal GPU constants.

Focused DATA6-1 tests pass **5/5**, including real official-vs-native descriptor parity for both supplied checkpoints. Surrounding INF1/ACCEL1/DATA6/DATA7 restart/cache-lineage slices pass **59 tests with four intentionally slow cases deselected**; additional descriptor/model-sweep/campaign-performance and DATA7 slices pass **29** and **16** tests respectively. After moving calibration authority into `doctor`, a final focused rerun of DATA6-1 non-slow, restart-reuse, and ACCEL1 compatibility tests passes **15 tests with two slow cases deselected**. Python compilation of all modified production modules also passes.

Real CuEq descriptor and deterministic DATA6 selection parity is **not certified in this environment** because CuEquivariance/OpenEquivariance and an authorizing CUDA runtime are absent. ACCEL1 already implements the parity/selection-stability authority; DATA6-1 binds the descriptor signature and batch calibration into that execution identity so the same real qualification can be rerun without redesign once the accelerator runtime is available. Machine-readable evidence is stored at `audits/analysis/mlff_mh1_data6_1_descriptor_evidence.json` with content digest `3b7323902c6bdf842833dd98cfa6d3016234f4879e93caa90743aa9b59a783a1`.

## Gate MH1-LINEAGE1 - replay, pseudolabel, reference-fit, and target-size provenance

Advance all artifacts that currently equate `foundation checkpoint SHA` with `foundation predictor`.

### MH1-LINEAGE1 concrete code changes

Primary files:

- `replay.py`;
- `reference_fit.py`;
- `target_size_convergence.py`;
- `production_materialization.py`;
- `production_qualification.py`;
- DATA7/DATA8 lineage serializers; and
- storage/restart migration readers.

Expected schema advancements include, subject to the implementation's existing numbering discipline:

- replay file/preparation artifact: current v3 -> head/generator-qualified v4 semantics;
- atomic reference fit: current v2 -> head-qualified v3 semantics;
- target-size training evidence: current v1 -> foundation-qualified v2 semantics;
- production materialization plan: current v6 -> head-qualified v7 semantics; and
- any downstream qualification record whose current foundation check is SHA-only.

For pseudolabel replay, bind a `foundation_label_generator_identity_digest` that includes the exact foundation potential plus numerically relevant inference realization. Existing MPA-0 replay geometries may be reused, but their MPA-0-generated labels are not transferred into an MH-1 preservation head. Relabel the same approved replay geometries under MH-1/`omat_pbe`/the qualified generator and publish a new replay artifact. True-DFT replay remains reusable when its independent reference-label protocol is compatible.

Foundation-residual atomic-reference fitting binds the scientific head-qualified foundation potential identity and extracts E0s by named head. DATA6-to-DATA8 materialization and production qualification compare the canonical foundation identity rather than raw checkpoint SHA.

### MH1-LINEAGE1 acceptance gate

All of the following intentional substitutions must fail:

- MPA-0 pseudolabel replay into an MH-1 campaign;
- MH-1 `omat_pbe` replay into another MH-1 source head;
- pseudolabel replay from an unqualified/different accelerator realization where generator identity is required;
- an E0/reference fit from the wrong source head;
- DATA6 evidence from the wrong source head; and
- target-size convergence evidence bound to a different foundation potential.

Historical single-head MPA-0 artifacts remain readable through exact singleton normalization.

### MH1-LINEAGE1 implementation record - 2026-08-14

MH1-LINEAGE1 is implemented on the DATA6-1 source snapshot. The remaining places that previously treated a checkpoint SHA as sufficient foundation provenance now distinguish **scientific foundation identity** from **numerically relevant pseudolabel-generator identity**. No optimizer, stopping/LR, selection, CV, or evaluation-scoring rule changes in this gate. DATA8 training execution remains deferred to MH1-TRAIN1.

`replay.py` advances pseudo-labeled replay to `mdstats.replay-file-artifact.v4` and `mdstats.replay-preparation-plan.v4`. Canonical pseudo-label artifacts no longer serialize `foundation_checkpoint_digest`; they carry `foundation_label_generator_identity_digest`, which is the exact `FoundationInferenceIdentity` for the source potential/head/dtype/backend/resolved kernel/adapter. Train and monitor pseudo-label artifacts must carry the same generator identity. Legacy v3 raw-SHA replay remains readable, but new canonical campaigns cannot create it. Existing approved replay **geometries** may therefore be reused when moving from MPA-0 to MH-1, while MPA-0-generated labels are not reinterpreted as MH-1 preservation labels. True-DFT replay is unchanged.

Canonical replay qualification in `campaign_cli.py` now resolves the real foundation potential, requires the doctor-frozen qualified acceleration realization, reconstructs the exact foundation inference identity, and binds that digest to the replay plan. A canonical pseudo-label campaign cannot manufacture provenance from an arbitrary/fake model file or from an unresolved acceleration request. Controlled pre-MH1 MPA-0 configurations normalized with `legacy_normalized=true` retain raw checkpoint-SHA replay semantics for read/restart compatibility only. Replay summaries expose the new generator digest separately from the legacy checkpoint digest.

`reference_fit.py` advances `AtomicReferenceFitRecord` to v3 for foundation-residual fits and binds `foundation_identity_digest` to the canonical **scientific** `FoundationPotentialIdentity`. Legacy v2 SHA-bound residual fits remain readable. `data7_bundle.py`, `data8_bundle.py`, `production_materialization.py`, and `production_qualification.py` now propagate and validate this exact scientific identity. Residual E0 evidence therefore cannot be moved between two heads of the same MH-1 bytes. The compatibility matcher accepts raw SHA lineage only when the source record itself is legacy, when the live identity is explicitly the lightweight/uninspected historical constructor, or when an inspected checkpoint proves a true singleton head. An inspected multi-head foundation always rejects head-blind raw-SHA lineage.

`TargetSizeTrainingEvidence` advances from v1 to v2. New Stage-B/Stage-C evidence carries `foundation_identity_digest`; legacy v1 raw checkpoint records still deserialize and retain their historical digest. Cross-size and Stage-B-to-Stage-C consistency now compare the generalized foundation lineage rather than a field whose semantics were implicitly SHA-only.

`ProductionMaterializationPlan` advances from v6 to v7 for newly built TRAIN2-authoritative plans while retaining existing readers for v6 and older supported schemas. The DATA6-to-DATA8 compatibility gate first uses `ModelCheckpointIdentity.foundation_potential_digest`; only legacy/head-blind sweeps fall back to their checkpoint SHA, and that fallback is then subjected to the fail-closed singleton/legacy rule above. The shared materialization recipe records both checkpoint SHA as byte identity and canonical foundation identity as scientific authority. Production qualification applies the same rule to residual-E0 completeness.

The locked real checkpoints demonstrate why this distinction is mandatory. The uploaded MH-1 `omat_pbe` and `omol` identities have the **same** checkpoint SHA `ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde` but canonical scientific digests `06bf87891d6addebd3ea300fa23fd6401f0b74897f5676394e99507d03c8fc59` and `77f92d39608f9875aae1dc4ba589c74ea6944fe9c88f5883a5e5867bf6067a0d`, respectively. Raw SHA lineage is rejected for the inspected six-head MH-1 model. The uploaded singleton MPA-0/default checkpoint has canonical digest `e6f6001827be216a9a8e8cb1829f2e2b996c846492f6f3975b6e6759064880dd`, and its matching historical raw SHA remains admissible. For MH-1/`omat_pbe` FP32, e3nn and pure-CuEq execution identities are also distinct (`fa91af1a4423422da683c388c1af3a4297e4c56edd60367725d32261386301c9` versus `f9ef007101c461db3748932d6553a2534b049ae6e739a3e179987b59d86c04a0`), so pseudolabel generator provenance cannot silently cross acceleration realizations. This records identity distinction only; real CuEq numerical qualification remains blocked by the current environment under MH1-ACCEL1.

Focused LINEAGE1 contract tests pass **5/5**. Replay/DATA7/DATA8/target-size propagation passes **57 tests**; production materialization passes **15**, production qualification **4**, and campaign CLI **43 with one pre-existing real-training-root skip**. A non-slow prior-gate/DATA8/DATA7/target-size slice passes **58 with six slow tests deselected**, and the legacy-schema/materialization/qualification slice passes **28**. The canonical v4 pseudolabel-as-persisted-baseline optimization in `campaign_execution.py` is deliberately deferred to MH1-EVAL1: until then, v4 replay recomputes the exact head-qualified foundation baseline instead of risking cache reuse under incomplete identity. Legacy persisted-pseudolabel reuse remains unchanged.

Machine-readable evidence is stored at `audits/analysis/mlff_mh1_lineage1_evidence.json` with content digest `356750755fd4e73224493e47f0570dbfc23ac8c71969b731c6bcb0d9463b7480`.

## Gate MH1-TRAIN1 - real DATA8 MH-1 fine-tuning under e3nn and CuEq

Once selected-head extraction and lineage are qualified, execute the real MACE training path rather than assuming DATA8 syntax implies runtime compatibility.

### MH1-TRAIN1 concrete code changes

Primary files:

- `data8_bundle.py`;
- `mace_compatibility.py`;
- `mace_realization.py`;
- training execution/preflight wrappers; and
- real-MACE focused tests.

DATA8 already carries much of the correct MACE 0.3.16 structure, including `foundation_model`, `foundation_head`, multi-head fine-tuning controls, and explicit replay files. Preserve that design while formalizing the distinct namespaces:

```text
foundation_head = omat_pbe
target_head     = target_head
replay_head     = pt_head
```

Extend the MACE source-compatibility lock to the selected-head/reconstruction and accelerator conversion entry points on which MH-1 depends. Real qualification must cover:

1. load source MH-1;
2. resolve `omat_pbe`;
3. source-head inference;
4. stock or compatibility-qualified selected-head extraction;
5. materialize a real DATA8 training configuration with replay;
6. execute a bounded/one-epoch multi-head replay fine-tune;
7. inventory produced heads/checkpoints;
8. extract the trained `target_head`;
9. reload it independently; and
10. perform finite numerical round-trip evaluation.

Run this realization once through the e3nn training path and once through the qualified CuEq path. Independent stochastic training trajectories need not be bit-identical, but both paths must satisfy the same DATA8 protocol and post-training qualification authority.

### MH1-TRAIN1 acceptance gate

MH-1 is production-training supported only after both configured backend paths can complete the bounded real-MACE realization required by their capability level, with no ambiguous source/replay/target head substitution and no unverified reconstruction workaround.

### MH1-TRAIN1 implementation record - 2026-08-14

MH1-TRAIN1 is implemented on the LINEAGE1 source snapshot for the fully qualified **e3nn** path. The gate deliberately keeps the scientific foundation potential and the executable training foundation as two different authenticated objects. The immutable DATA8 protocol continues to bind the original six-head MH-1/`omat_pbe` scientific identity (`ec00a270...c5dde`, potential digest `06bf8789...fc59`), while MACE 0.3.16 is pointed at the EXTRACT1-qualified single-head training checkpoint (`7b6f3cce...545e`, qualification digest `0f49db0f...365`). This prevents the 0.3.16 reconstruction workaround from replacing the scientific source identity in replay, residual-E0, DATA6, or audit lineage.

The schema boundary advances only where that distinction is required. `TrainingProtocolIdentity` advances to v7 when a selected-head training foundation is present and records the derived checkpoint reference/SHA plus EXTRACT1 qualification digest. Production materialization advances to v8 so the same qualification survives restart and DATA8 staging. `MaceConfigRealizationRecord` advances to v4 and authenticates the foundation file SHA actually parsed by the MACE CLI, the exact `foundation_head`, and `multiheads_finetuning`. `MacePrecisionTransitionRecord` advances to v2 so precision auditing checks the executable selected-head checkpoint while preserving the original scientific foundation identity. Historical v6/v7/v3/v1 payloads retain schema-preserving readers and legacy digests.

The real DATA8 acceptance job uses one target training configuration and one replay training configuration solely to bound wall time while preserving the complete replay/head contract. The realized MACE configuration parses `foundation_head=omat_pbe`, `multiheads_finetuning=True`, and the qualified derived checkpoint SHA. The bounded e3nn run completes one epoch with exactly **2 gradient updates**, reports both `pt_head` and `target_head`, and writes an epoch checkpoint plus the final two-head model. The trained model remains float64, retains `use_edge_irreps_first=True`, and preserves the MH-1 first projection `128x0e`; therefore the original stock-foundation reconstruction defect is not reintroduced by the trained model.

Stock MACE target-head extraction succeeds on the trained two-head model without the EXTRACT1 compatibility shim. The resulting single `target_head` model is float64, retains the same architecture flag/projection, reloads independently, and evaluates four held target configurations with finite energy, forces, and stress. The TRAIN1 precision-transition v2 record and critical-precision audit both pass. The real artifact SHAs are recorded in the machine-readable evidence rather than treated as package constants.

The real e3nn CLI/config realization test passes independently. The permanent bounded-epoch integration test is marked slow because the combined train -> inventory -> extraction -> evaluation helper exceeds this tool harness's single-invocation execution window even though the individual scientific phases complete successfully; the authenticated gate evidence therefore records the same immutable job phase-by-phase. This is an execution-harness limitation, not a MACE training failure.

CuEq training remains **non-authorizing and runtime-blocked** in this environment because CuEquivariance/OpenEquivariance and an authorizing CUDA runtime are absent. No e3nn substitution is made. Under MACE 0.3.16, training realization remains pure CuEq even when hybrid CuEq+OEQ is available for inference, so the CuEq side of TRAIN1 must be rerun when the accelerator runtime is available. No stopping rule, LR policy, CV, target/replay scoring, or evaluation-selection rule changes are introduced by TRAIN1.

Focused TRAIN1 protocol/migration tests pass **14 with two slow tests deselected** in the main slice; the real CLI realization test passes independently; the final prior-gate/TRAIN2/legacy compatibility slice passes **44 with five slow tests deselected**; and production materialization/qualification passes **19**. The full chained slow helper remains harness-timeout-limited as described above, while its training, extraction, evaluation, and precision phases all have authenticated passing evidence.

Machine-readable evidence is stored at `audits/analysis/mlff_mh1_train1_training_evidence.json` with evidence digest `6f174165cf20bb56731c88774b8a8c68e208e9fa37057de1816cd6dbc2be7168`.

## Gate MH1-EVAL1 - canonical foundation baseline in evaluation and PES verification

Remove downstream configuration knobs that can silently choose a foundation baseline head independently of `[foundation].head`.

### MH1-EVAL1 concrete code changes

Primary files:

- `campaign_execution.py`;
- `foundation_audit.py`;
- `pes_verify.py`;
- evaluation policy serializers/caches; and
- campaign CLI configuration/reporting.

The checkpoint evaluation policy retains candidate `target_head` and `pt_head` names because those are properties of trained candidates. Foundation baseline prediction, replay baseline comparison, and PES foundation comparison derive from the canonical `FoundationPotentialIdentity`/`FoundationInferenceIdentity` instead of an independent `replay_baseline_head` or `pes_foundation_head` authority.

Foundation-audit reports visibly identify foundation family, exact source head, checkpoint identity, execution backend/mode, target reference protocol, and any descriptive source-head theory/domain metadata. Theory metadata is informative/provenance-bearing and may warn about a reference-level difference, but does not automatically forbid transfer learning between levels of theory.

### MH1-EVAL1 acceptance gate

1. no new-campaign evaluation/PES consumer can independently select a source-foundation head;
2. DATA6 cached baseline predictions are reused only under exact matching foundation/inference identity;
3. target/replay candidate heads remain distinct from source foundation head; and
4. the completed target-first EVAL2 and physical-selection authority remains scientifically unchanged.

### MH1-EVAL1 implementation record - 2026-08-14

MH1-EVAL1 is implemented on the TRAIN1 source snapshot. The source-foundation baseline is now an explicit canonical authority composed of `FoundationPotentialIdentity` plus `FoundationInferenceIdentity`; the trained-candidate heads remain separately named `target_head` and `pt_head`. New canonical campaigns therefore no longer derive baseline authority from `evaluation.replay_baseline_head` or `verification.pes_foundation_head`. Those fields remain readable only as legacy MPA-0 compatibility aliases, and generalized campaign policy construction derives the source head from `[foundation].head` through the inspected potential identity.

`CheckpointEvaluationPolicy` advances to v7 when canonical foundation identities are present. The policy embeds both scientific and execution identities and rejects an independent non-empty legacy baseline-head selector. Its source-head accessor resolves from the canonical potential for generalized campaigns and from the historical selector only for legacy records. The existing target/replay candidate head names and EVAL2 target-first/full-validation authority are unchanged. No stopping, LR, CV, target/replay weighting, ranking, or physical-selection rule is modified by this gate.

Persistent evaluation prediction keys now distinguish source-foundation predictions from ordinary candidate predictions. Foundation keys advance to `mdstats.evaluation-prediction-key.v2` and bind the exact `FoundationInferenceIdentity` digest in addition to model SHA/head/dtype/device/acceleration policy. Candidate prediction keys deliberately remain on the historical v1 schema so existing candidate checkpoint caches are not invalidated unnecessarily. A change in resolved kernel realization, MACE/runtime identity, or source potential/head therefore invalidates foundation-baseline cache reuse even when checkpoint bytes and head text happen to match.

DATA6 baseline reuse is likewise fail-closed. Canonical DATA6 evidence is reusable only when checkpoint SHA, scientific potential digest, exact source head, inference digest, dtype/device, and acceleration-policy identity all match the live evaluation policy. Canonical head-qualified evidence is never down-cast into the legacy head-blind path. The deferred LINEAGE1 optimization for replay pseudolabels is now closed: v4 foundation pseudolabels can be reused as persisted baseline predictions only when their `foundation_label_generator_identity_digest` equals the exact live `FoundationInferenceIdentity` digest. Legacy v3 pseudolabel reuse remains restricted to the historical head-blind singleton path.

`FoundationTargetAudit` advances to v2 when canonical identities are present while preserving v1 round-trip semantics for historical audits. Canonical audit authority binds both potential and inference identities and verifies them against the live DATA6 bundle. Audit reporting now visibly prints foundation family, exact source head, checkpoint SHA, backend, resolved kernel, dtype, descriptive source-head domain/theory, the authenticated target electronic-structure core-label protocol digest(s), and the target-role freeze. The descriptive source-head labels are reporting-only; they do not enter scientific identity and therefore do not forbid intentional transfer learning between electronic-structure reference levels.

`PESVerifyCampaignRecord` likewise advances to v2 for canonical campaigns. PES foundation prediction derives its head from the audit's `FoundationPotentialIdentity`, its calculator realization from the audit's `FoundationInferenceIdentity` plus the doctor-frozen acceleration realization, and its cache-reuse check compares both nested identities. `predict_mace_model_on_probe` now accepts optional canonical foundation identities for this source-foundation use case and validates model SHA, head, dtype, and backend before constructing the calculator. Candidate PES/deployment callers preserve the historical interface and remain target-only.

Focused EVAL1 identity/cache/audit/PES tests pass **6/6**. The combined campaign/evaluation/PES/legacy regression passes **121 with two expected environment-dependent skips**, and an additional MLCV/MF2 slice passes **29** with one pre-existing textual specification assertion deselected. That assertion searches for a literal `checkpoint_strategy = "mlcv_nested_cv"` source assignment that had already disappeared in the TRAIN1 predecessor after CONFIG1 parameterized template construction; it is not an EVAL1 regression. The completed EVAL2 tests pass unchanged.

Machine-readable evidence is stored at `audits/analysis/mlff_mh1_eval1_evaluation_evidence.json` with content digest `9723c726edb8315fe57731a739ec7ab745fc62f8748c7a102a6e35d260462379`.

## Gate MH1-DEPLOY1 - target-head export, backend parity, and ML-IAP deployment

Preserve the existing deployment architecture: a multi-head foundation is adapted, the qualified `target_head` is extracted to a single-head production MACE model, and deployment verification acts on that exact target-only artifact.

### MH1-DEPLOY1 concrete code changes

Primary files:

- `deploy_verify.py`;
- `relax_verify.py` and dynamics/critical-precision calculator construction as needed;
- target-head materialization/export helpers; and
- MACE/ML-IAP deployment tests.

The desired chain is:

```text
MH-1 multi-head foundation
        |
        v
selected omat_pbe foundation
        |
        v
multi-head replay fine-tune
        |
        v
qualified target_head
        |
        v
single-head production MACE model
        |
        v
ML-IAP/LAMMPS artifact
```

ML-IAP is not required to expose arbitrary source multi-head semantics. Production deployment consumes the extracted single target head. When the campaign backend is CuEq, the exact extracted model must still satisfy the existing selected-checkpoint -> target-only export -> deployment parity authority; e3nn remains available as an independent reference verification path.

### MH1-DEPLOY1 acceptance gate

1. extracted target-head MACE predictions match the evaluated candidate according to DEPLOY-VERIFY1;
2. the ML-IAP artifact matches the target-only model under existing deployment tolerances;
3. both MH-1/e3nn and MH-1/CuEq campaigns can reach the same deployment contract; and
4. foundation selected-head compatibility artifacts never become confused with final learned target-head exports.

### MH1-DEPLOY1 implementation record - 2026-08-14

MH1-DEPLOY1 is implemented on the EVAL1 source snapshot through the learned-target export and deployment-lineage boundary. The canonical deployment identity is now explicitly a **trained-candidate -> learned-target** transform, not a foundation-head extraction. `TargetHeadDeploymentIdentity.v1` requires `source_artifact_role = trained_candidate_multihead`, `target_artifact_role = learned_target_head`, the exact source and target model SHA256 values, the selected `target_head`, deployment dtype, run-plan digest, and EVAL2 run-record digest. It therefore cannot represent the EXTRACT1 compatibility artifact (`foundation_multihead -> selected_foundation_head`) and fails closed if those roles are substituted.

`DeployVerifyRunRecord` advances to v2 for canonical campaigns. Its target-head export digest and ML-IAP export digest both bind the `TargetHeadDeploymentIdentity` digest. Historical v1 records remain readable and retain their original digest semantics; canonical generalized campaigns do not reuse a v1 deployment record as current evidence. The ML-IAP export path also records a separate runtime-capability identity so a change in the exporter/runtime cannot be mistaken for the same deployment transform. No training, stopping/LR, EVAL2 scoring, or foundation EXTRACT1 policy changes are introduced by this gate.

A real TRAIN1-derived learned target model was regenerated and compared directly against the trained two-head MACE candidate using the candidate's explicit `target_head`. On four held target-validation configurations in float64, the maximum source-vs-target difference is `1.7763568394002505e-15 eV` in total energy, `0.0 eV/A` in forces, and `0.0 eV/A^3` in stress under `rtol=1e-9`, `atol=1e-10`. The trained multi-head model SHA256 is `95c85201eefb6a6506a22b735fa66ddaf9e0cca9b5710c7e00fe6ad02d430ec7`; the independently extracted learned-target model SHA256 is `e03abd03af63def40b0ec1a736729aa00194ba9807514b23ff15930e5f1eb77d`. This closes DEPLOY1 acceptance item 1 and confirms that the learned target artifact, not the EXTRACT1 selected foundation artifact, is the production MACE source.

The gate also establishes an important MACE 0.3.16 deployment-runtime constraint that was not visible at planning time. The official `mace.cli.create_lammps_model --format=mliap` path unconditionally invokes `run_e3nn_to_cueq(...)` before serializing an ML-IAP artifact. Consequently, **CuEquivariance is a deployment-time prerequisite for the official MACE 0.3.16 ML-IAP exporter even when the campaign was trained and evaluated with e3nn**. `MliapExportRuntimeCapability.v1` now probes exact MACE version plus `cuequivariance` and `cuequivariance_torch` availability before export and fails closed when the runtime is not qualified. No custom unqualified e3nn-only ML-IAP exporter is added.

The supplied locked runtime contains MACE 0.3.16 but does not contain CuEquivariance. A real invocation of the official exporter therefore fails during the mandatory e3nn->CuEq conversion with unexpected `products.*.symmetric_contractions.weight` keys rather than producing an ML-IAP artifact. The current host also has no `lmp` executable, so an actual LAMMPS run-0 comparison cannot be performed here. DEPLOY1 acceptance items 2 and 3 are therefore **environment-blocked, not passed**: the mdstats deployment contract and fail-closed capability checks are implemented, but real ML-IAP/LAMMPS certification must be rerun in the final CuEq/OEQ + ML-IAP-enabled LAMMPS environment. This does not permit a silent e3nn fallback or a reinterpretation of missing deployment evidence as success.

Focused and affected deployment/runtime regression passes **69 tests with three expected environment-dependent skips**; the campaign CLI regression passes **43 tests with one expected real-training-root skip**. One historical deployment specification test that asserts the old literal release text `0.20.140a0` remains outside regression interpretation, as in predecessor gates. Machine-readable evidence is stored at `audits/analysis/mlff_mh1_deploy1_deployment_evidence.json` with content digest `16f7b7e821831d024c0d8f52c57f1f05343eba44f7fe4a3206ee1b4f9ca44ec2`.

**Gate status:** implementation and learned-target parity are complete. Official ML-IAP export parity and LAMMPS run-0 parity remain explicitly runtime-blocked until the required CuEquivariance stack and LAMMPS executable are available. MH1-CERT1 must carry those blocked items forward and may not certify the full generated-default CuEq deployment matrix without them.

## Gate MH1-CERT1 - full regression, storage, migration, and documentation closure

Close the revision with a deliberate cross-product qualification matrix and storage/restart audit.

### Required real-model certification matrix

| Foundation | Head | Backend | Required qualification |
|---|---|---|---|
| MPA-0 | actual singleton | e3nn | full regression |
| MPA-0 | actual singleton | CuEq | full regression |
| MH-1 | `omat_pbe` | e3nn | full production |
| MH-1 | `omat_pbe` | CuEq | full production and generated default |
| MH-1 | second actual checkpoint head | e3nn | identity + inference + DATA6 lineage |
| MH-1 | second actual checkpoint head | CuEq | identity + accelerator/descriptor parity |
| MH-1 | invalid/missing head | any | hard failure |

Use a second head discovered from the real checkpoint rather than assuming a static published head list.

### Storage/reclamation changes

Classify new artifacts explicitly:

- original foundation checkpoint: external/immutable source root;
- foundation inspection/identity: small durable provenance;
- selected-head compatibility artifact: durable when required by training lineage;
- acceleration realization/parity record: durable campaign evidence;
- DATA6 predictions/descriptors: rebuildable cache under existing retention rules; and
- temporary calibration/intermediate files: reclaimable after authenticated durable evidence exists.

The storage manager must never treat the original foundation or a qualified derived selected-head checkpoint required by DATA8 lineage as an ordinary disposable DATA6 cache.

### Real-model test-fixture policy

Do not package the large MACE foundation checkpoints inside the normal mdstats source distribution. Real integration tests accept external paths such as:

```text
MDSTATS_TEST_MH1_MODEL=/path/to/mace-mh-1.model
MDSTATS_TEST_MPA0_MODEL=/path/to/mace-mpa-0-medium.model
```

and may validate the development fixture SHAs when those locked fixtures are supplied. Unit tests continue to use lightweight/mock/generated models where real foundation bytes are unnecessary.

### MH1-CERT1 acceptance gate

The revision closes only when:

1. all required matrix cells pass their declared capability level;
2. historical authenticated MPA-0 campaigns and artifacts remain readable/restartable;
3. ambiguous historical multi-head artifacts fail closed;
4. storage cleanup preserves every new root/durable lineage artifact;
5. generated documentation/user guidance names MH-1/`omat_pbe`/CuEq as the default and e3nn as explicit fully supported fallback/reference;
6. the MACE-0.3.16 MH-1 extraction shim, if needed, is version/architecture guarded and has a self-disablement test;
7. no completed TARGET-DATA2/TRAIN2/EVAL2/physical-selection/LOCKED-TEST2 scientific rule has changed without an explicit separately versioned revision; and
8. the original MPA-0 and MH-1 fixture checkpoints remain byte-identical throughout testing.

### MH1-CERT1 implementation record - 2026-08-14

MH1-CERT1 closes the **mdstats implementation, migration, storage, and reference-backend certification work** for generalized MACE foundations. It does **not** declare the complete generated-default `MACE-MH-1 / omat_pbe / CuEq` production matrix certified on the present host. The remaining failure to close the full matrix is environmental and is carried forward explicitly: the supplied runtime has no CuEquivariance, no OpenEquivariance, no authorizing CUDA runtime, and no ML-IAP-capable LAMMPS executable. Missing accelerator/deployment evidence is never reinterpreted as e3nn success and never triggers a silent backend substitution.

The final real-model matrix is:

| Foundation | Head | Backend | CERT1 status |
|---|---|---|---|
| MPA-0-medium | `default` | e3nn | **PASS** - locked BASE0 regression and real numerical reference remain green |
| MPA-0-medium | `default` | CuEq | **BLOCKED-RUNTIME** - CuEq/CUDA runtime absent |
| MH-1 | `omat_pbe` | e3nn | **PASS through learned target-head parity; deployment runtime-blocked** - identity, inference, E0, DATA6/DATA7, EXTRACT1, bounded DATA8 replay training, EVAL1/PES, and learned-target parity pass; official MACE 0.3.16 ML-IAP export still requires CuEq |
| MH-1 | `omat_pbe` | CuEq | **BLOCKED-RUNTIME** - generated default cannot be fully authorized on this host |
| MH-1 | `omol` | e3nn | **PASS** at the declared identity + inference + DATA6-lineage level |
| MH-1 | `omol` | CuEq | **BLOCKED-RUNTIME** - accelerator/descriptor parity cannot be executed |
| MH-1 | invalid or missing head | any | **PASS fail-closed** - rejected before calculator construction |

The second-head cell uses the actual `omol` head discovered from the locked six-head checkpoint. Under e3nn the provider is constructed with explicit `head="omol"`, returns finite energy/forces and native invariant descriptors, and produces a scientific/DATA6 identity distinct from `omat_pbe`. The original locked model bytes remain unchanged: MH-1 SHA256 is `ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde` and MPA-0-medium SHA256 is `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638` before and after certification.

CERT1 also closes the new storage/restart boundary. The external `[paths].foundation_model` remains a protected immutable input. `.mdstats/foundation-selected-head/` is now classified as the named `selected_head_training_foundation` family with `RESTART_CRITICAL` retention and both automatic and manual reclamation prohibited. Deleting it would lose the capabilities `mh1_selected_head_training_restart` and `exact_training_foundation_reproduction`. STOR4 cleanup/compaction plans explicitly advertise `qualified_selected_head_training_foundation` and `foundation_identity_and_acceleration_realization` as preserved capabilities and never nominate the selected-head artifact for cleanup. DATA6 descriptors/predictions remain rebuildable under their existing cache rules; small identity/acceleration evidence remains protected campaign-state authority.

The final semantic audit found no canonical raw-SHA-only foundation lineage. New replay pseudolabel provenance binds `FoundationInferenceIdentity`; residual-E0/reference-fit, target-size, DATA6->DATA8, and production qualification bind the exact head-qualified scientific foundation identity. Raw `foundation_checkpoint_digest` fields that remain in code are versioned legacy-schema readers only. Head-blind legacy evidence is still accepted only under the previously defined authenticated singleton/uninspected compatibility rules and cannot be promoted to inspected multi-head MH-1 by assumption.

CERT1 intentionally does not reopen completed scientific policies. `train2_policy.py`, `eval2.py`, `lightweight_rank.py`, and `target_size_convergence.py` are byte-identical to the DEPLOY1 predecessor, with SHA256 values `9e404ca92a59840bd544d53d3890498fcec2563738e87e03fb46d254c0c46c11`, `1e96949bbbfdb61c3c7cdeb92e5bccc46b96b884f84f34b211eb2a75843cb577`, `c4dafbf233ed1075d4b8b6b1c37d4a7205ab593b0c360f9346cf7e08d99a7ac1`, and `717a60bfdb3da7639efdb0974be0241661925c2e07c93da4c3e847f9eee74e6f`, respectively. TRAIN2/EVAL2 functional tests pass in a fresh process, and no target-first stopping, LR, ranking, validation, physical-selection, or locked-test rule is changed by CERT1.

Current final verification includes 39 passing CERT1/storage tests with the two slow real cells deselected, the two real CERT1 fixture cells passing separately, 35 fresh-process TRAIN2/EVAL2 functional tests, and all four BASE0 MPA-0 regression tests including the real e3nn reference. The broad 185-file MLFF sweep produced **996 passes**. Its 53 observed failures are not treated as CERT1 regressions: 51 are locked/pre-existing archival release/source-text/specification assertions, while two TRAIN2 failures are order-pollution effects that pass in a fresh isolated process. Historical specification evidence is deliberately not rewritten merely to make old literal assertions agree with the generalized post-0.20.177 implementation.

Machine-readable certification evidence is stored at `audits/analysis/mlff_mh1_cert1_certification_evidence.json` with content digest `873375af6bb75b76ccbd10f7d1cffe3531b9841d1e912ce7b513d6ffaf067beb`.

**Gate status:** the planned mdstats code/migration/storage/documentation implementation is closed, and the e3nn/reference cells pass their declared qualification levels. The full revision acceptance criterion remains **runtime-blocked** because the generated default requires real MH-1/`omat_pbe` CuEq authorization plus official ML-IAP export and LAMMPS run-0 parity. The next action is a runtime-certification rerun of ACCEL1/DEPLOY1/CERT1 in an environment containing CuEquivariance, OpenEquivariance, usable CUDA, and an ML-IAP-capable LAMMPS executable; no additional architecture gate is required before that rerun.

## Post-CERT1 doctor hotfix: runtime source compatibility, optional OEQ, and acceleration qualification

A post-CERT1 runtime report exposed three coupled doctor failures in a real CuEq workstation environment: the exact MACE 0.3.16 source-byte lock rejected the installed package, OpenEquivariance absence was treated as a blocking CuEq dependency, and acceleration qualification raised `NameError: np is not defined` while constructing the deterministic parity corpus. Replay then emitted a secondary failure because no acceleration realization had been frozen.

The hotfix preserves the fail-closed design while correcting the authority boundaries:

1. **NumPy scope is corrected.** `_doctor_acceleration_corpus()` imports NumPy in the function that uses it. Acceleration qualification can therefore reach the actual e3nn/CuEq numerical parity test rather than failing in corpus construction.
2. **OpenEquivariance is optional by default.** Under the already-frozen ACCEL1 contract, MACE 0.3.16 training uses pure CuEq even when hybrid inference is available. Therefore `cueq` authorization requires the CuEquivariance core/Torch/ops stack and successful pure-CuEq parity; OEQ is required only when an explicit runtime-freeze policy asks for it. When OEQ is installed and hybrid inference passes, MH-1 may still resolve to `cueq_oeq_hybrid` for inference while retaining `cueq_pure` for training.
3. **The exact MACE byte lock is strong evidence, not the sole runtime authority.** Exact hashes remain recorded and preferred. If installed `mace-torch==0.3.16` source bytes differ, mdstats now performs a positive semantic source probe covering the fixed-file DATA8 training behavior, selected-head reconstruction entry points, foundation-head CLI semantics, and CuEq CLI support. Only an exact byte match **or** a passing semantic probe qualifies the source runtime; version equality alone is not sufficient. The mismatch is reported as a warning with the differing source files rather than silently ignored.
4. **Legacy DEP0 evidence remains digest-stable.** Runtime-freeze records advance to v2 for semantic-source evidence, while v1 records deserialize using their historical derived fields and failure strings so existing campaign state is not invalidated.
5. **Replay no longer reports a cascading pseudo-independent failure.** For a canonical `external_pseudolabel` campaign, replay qualification is deferred when doctor has not qualified the acceleration realization in the current run. The original acceleration failure remains the blocking authority; replay is retried automatically after doctor succeeds.

The focused post-hotfix regression covers DEP0, ACCEL1, CONFIG1, legacy schemas, campaign doctor plumbing, LINEAGE1, pseudolabel replay, true-label replay, and replay-degradation semantics. It passes **106 tests**, with two environment-dependent skips and two deliberately slow cases deselected. The prior DEP0 v1 machine-readable evidence still round-trips with its original content digest. Machine-readable hotfix evidence is stored at `audits/analysis/mlff_mh1_doctor_hotfix1_evidence.json`.

**Operational consequence:** a workstation with CuEquivariance installed but without OpenEquivariance may now qualify a pure-CuEq MH-1 campaign. A source-byte mismatch in an otherwise semantically compatible MACE 0.3.16 installation no longer blocks doctor. If the semantic source probe, pure-CuEq numerical parity, or any later realization gate fails, the campaign still fails closed and no e3nn fallback is applied automatically.

## Post-CERT1 doctor hotfix 2: acceleration-subroutine warning consolidation and parity diagnostics

A subsequent real CuEq doctor run reached the intended ACCEL1 numerical qualification but exposed high-volume third-party warning noise during e3nn/CuEq calculator construction and TorchScript conversion. The repeated families were MACE's tensor-copy construction `UserWarning` from `mace/modules/models.py` and Python/TorchScript's repeated instance-annotation `UserWarning` emitted through `ast.py`. These warnings are upstream runtime noise rather than independent mdstats qualification failures.

The existing `mace_runtime_warning_scope` already had narrow fingerprints for both families, but ACCEL1's realization qualification was outside that warning boundary. The hotfix therefore wraps both `qualify_e3nn_realization()` and `qualify_cueq_realization()` in the standard MACE runtime warning scope. The scope now explicitly forces only these two known high-volume `UserWarning` families through capture so repeated emissions are reliably observed even when MACE/Torch resets internal warning registries. Other `UserWarning` categories retain the caller's normal filtering behavior and unrelated warnings are replayed unchanged.

One ACCEL1 qualification now emits at most one `MaceRuntimeCompatibilityWarning` for the captured upstream families. The consolidated warning reports the operation, total warning count, unique warning groups, group counts, compact source, and runtime versions. Process-level deduplication remains active, so repeating the same warning signature later in the same process does not wash out useful campaign output. The underlying warnings are not reclassified as success and the actual CuEq parity decision remains fail-closed.

The same hotfix improves a failed CuEq realization message without changing any numerical tolerance. When pure CuEq or CuEq+OEQ parity fails, the failure reason now includes compact maximum absolute differences for energy, force, stress, and invariant descriptors together with whether deterministic selection fingerprints are identical. This makes a real workstation failure diagnostically actionable while preserving the ACCEL1 FP32/FP64 tolerance authority and the rule that MACE 0.3.16 training requires qualified pure CuEq.

Focused warning/ACCEL1 tests pass 26 tests in non-slow mode. The campaign/configuration/doctor/ACCEL1/warning regression passes 80 tests with one expected environment-dependent skip. Tests explicitly reproduce multiple copies of the two warning families and assert that the user-visible result is exactly one consolidated `MaceRuntimeCompatibilityWarning`. Machine-readable evidence is stored at `audits/analysis/mlff_mh1_doctor_hotfix2_warning_evidence.json`.

**Operational consequence:** rerunning `doctor` may still fail if `cueq_pure` is genuinely numerically non-equivalent to e3nn, but the failure is no longer buried under repeated MACE/Torch subroutine warnings. The failure line also reports the parity deltas needed to decide whether the issue is energy/force/stress, descriptor parity, or DATA6 selection stability. No parity threshold is relaxed and no automatic e3nn fallback is introduced.

## Concrete implementation footprint

The expected production code footprint is deliberately concentrated at foundation identity, realization, lineage, and backend boundaries rather than the scientific selector itself.

| File/module | Planned responsibility change |
|---|---|
| new `foundation.py` | canonical MACE foundation family/spec/inspection, scientific identity, architecture signature, head resolution |
| `protocol.py` | advance foundation checkpoint identity to canonical head-qualified semantics and legacy normalization |
| `campaign_cli.py` | MH-1/`omat_pbe`/CuEq defaults; `[foundation]`; head-aware provider/E0; doctor and canonical evaluation/PES plumbing |
| `model_features.py` | DATA6 model identity advancement; architecture-aware descriptor adapter/signature; head/backend-aware caching |
| `acceleration.py` | paired e3nn/CuEq qualification, pure/hybrid realization, persisted acceleration evidence |
| `replay.py` | generator-qualified pseudolabel provenance and schema advancement |
| `reference_fit.py` | named-head E0 and scientific foundation identity binding |
| `target_size_convergence.py` | head-qualified foundation lineage for training evidence |
| `production_materialization.py` | replace SHA-only DATA6/DATA8 compatibility with canonical foundation identity |
| `production_qualification.py` | head-qualified production gate lineage |
| `data8_bundle.py` | formal source/target/replay head namespaces; retain existing real MACE replay-file realization |
| `mace_compatibility.py` | MACE 0.3.16 source/runtime contract including MH-1 reconstruction and acceleration entry points |
| `mace_realization.py` | real selected-head extraction, bounded MH-1 fine-tuning, target-head round-trip qualification |
| `campaign_execution.py` | canonical foundation baseline identity; head-aware DATA6 prediction reuse; evaluation schema advancement as required |
| `foundation_audit.py` | visible family/head/backend/reference-level provenance |
| `pes_verify.py` | canonical source foundation identity rather than independent head selector |
| `deploy_verify.py` | MH-1 target-head/export/deployment qualification under both backend policies |
| `relax_verify.py` / dynamics/critical precision | head/backend-aware calculator construction where foundation/candidate inference still occurs |
| storage/restart serializers | recognize new durable foundation/acceleration/derived-head artifacts and legacy migrations |

The expected focused test additions include foundation identity/head resolution, generated defaults, e3nn/CuEq MH-1 inference, pure/hybrid accelerator parity, descriptor parity and selection stability, replay/reference-fit/target-size lineage rejection, real selected-head extraction, real MH-1 DATA8 training, evaluation/PES foundation identity, production materialization, deployment, and legacy MPA-0 migration.

## Ordered implementation sequence

The gates are implemented in this exact dependency order unless a later architecture revision explicitly changes it:

```text
MH1-DEP0
    dependency/runtime freeze
        |
        v
MH1-BASE0
    locked MPA-0 regression baseline
        |
        v
MH1-ID1
    generalized foundation identity + inspection + migration
        |
        v
MH1-CONFIG1
    MH-1/omat_pbe/CuEq generated defaults
        |
        v
MH1-INF1
    exact head-aware inference/E0/DATA6 root identity
        |
        v
MH1-EXTRACT1
    MH-1 architecture-faithful selected-head extraction
        |
        v
MH1-ACCEL1
    e3nn reference + CuEq pure/hybrid qualification
        |
        v
MH1-DATA6-1
    descriptor adapter, batching, DATA6/DATA7 parity
        |
        v
MH1-LINEAGE1
    replay/E0/reference-fit/target-size/materialization lineage
        |
        v
MH1-TRAIN1
    real DATA8 MH-1 multi-head replay fine-tuning
        |
        v
MH1-EVAL1
    canonical evaluation/PES foundation baseline
        |
        v
MH1-DEPLOY1
    target-head export + ML-IAP deployment
        |
        v
MH1-CERT1
    full cross-model/backend regression and migration closure
```

Each gate must append an implementation record to this manual when completed. Later gates may not reinterpret a failed earlier identity/parity gate as a warning merely to continue execution.

## Explicit non-goals for the MH-1 revision

To keep the verification matrix bounded, this revision does not add:

- automatic foundation-model downloading;
- arbitrary remote MACE-family discovery;
- new model-family-specific DATA6/FPS scientific weights;
- new MH-1-specific force/energy acceptance thresholds;
- LoRA, frozen-layer, or alternative fine-tuning algorithms;
- a `torch.compile` optimization campaign;
- a new long-range/electrostatic correction implementation;
- a new physical replay scoring rule; or
- any reopening of completed locked-test evidence.

Those can be separate, explicitly versioned revisions after the generalized foundation contract is proven.

## Historical completion rule for the generalized MACE/MH-1 revision

**Supersedence note:** this rule records the original pre-workstation-certification target. The post-CERT1 runtime revision and the post-CERT optimization roadmap below are authoritative for current generated defaults and future CuEq authorization.

The revision is complete only when **MACE-MH-1 + `omat_pbe` + CuEq is a genuinely generated, qualified, end-to-end production campaign path**, not merely a configuration accepted by the CLI, while **MACE-MH-1 + `omat_pbe` + e3nn remains an equally complete explicit path and numerical reference**. MPA-0 remains supported without scientific reinterpretation, every foundation-sensitive artifact is exact-head aware, pseudolabel and E0 lineage is generator/foundation correct, the known MACE 0.3.16 selected-head reconstruction defect is either bypassed by a proven upstream fix or a minimal parity-qualified version guard, and the existing target-first/physical/locked-test scientific authority remains unchanged.


## Post-CERT1 doctor hotfix 3: phase-correct CuEq qualification

Runtime testing on the intended RTX 3090 environment exposed a large pure-cuEquivariance mismatch for the original six-head MH-1/`omat_pbe` foundation (representative doctor evidence: `Emax=1.418e+00`, `Fmax=7.567e-01`, `Smax=1.332e-02`, `Dmax=2.464e+00`, with non-identical DATA6 selection). These discrepancies are far outside the ACCEL1 parity tolerances and must remain fail-closed.

The previous ACCEL1 implementation incorrectly reused that source-foundation pure-CuEq parity record as the *training* parity record. TRAIN1 does not train from the original six-head checkpoint under MACE 0.3.16: it trains from the EXTRACT1-qualified derived single-head `omat_pbe` checkpoint. Therefore source-foundation inference parity and training-foundation parity are distinct executable contracts and must be measured independently.

Hotfix 3 changes the CuEq qualifier as follows:

1. Source-foundation inference parity is measured on the original foundation checkpoint/head against e3nn. Pure CuEq and, when available, CuEq+OpenEquivariance hybrid are independently tested.
2. Training-foundation parity is measured on the exact executable training checkpoint. For MH-1 this is the EXTRACT1-qualified derived `omat_pbe` artifact; for legacy/single-head foundations it defaults to the source checkpoint.
3. MACE 0.3.16 training remains authorized only when the executable training foundation passes *pure* CuEq parity, because the 0.3.16 trainer disables OEQ when CuEq training is enabled.
4. A CuEq campaign is fully qualified only when both an inference realization and the independent training realization pass. A passing hybrid inference path may therefore coexist with a passing pure-CuEq training path.
5. If source-foundation pure CuEq fails while the derived training foundation passes, doctor reports those facts separately. It no longer claims that training is unsafe merely from the multi-head source-model mismatch.
6. No tolerance is relaxed and no silent e3nn substitution is introduced.

This hotfix is also aligned with the upstream MACE defect history: MH-1 multi-head CuEq parity has had large reported discrepancies while MPA-0 remains numerically stable, and upstream development continues to add regression coverage for hybrid multi-head parity. The final mdstats authority remains its own paired numerical qualification on the exact runtime/model artifacts.


## Post-CERT1 runtime revision - MH-1 generated backend default changed to e3nn

**Status:** implemented after real RTX 3090 qualification of MACE 0.3.16 / MACE-MH-1 `omat_pbe`. This section supersedes the earlier CONFIG1/CERT1 statements that named CuEq as the generated MH-1 default; those earlier sections remain historical implementation records.

The real production workstation demonstrated that acceleration availability is not sufficient evidence of numerical equivalence. On the original six-head MH-1 checkpoint, pure CuEq failed paired e3nn parity with approximately `Emax=1.375 eV`, `Fmax=0.7522 eV/Angstrom`, `Smax=1.263e-2 eV/Angstrom^3`, `Dmax=2.336`, and a different deterministic selection fingerprint. CuEq+OpenEquivariance hybrid inference also failed materially (`Emax=1.453 eV`, `Fmax=0.7523 eV/Angstrom`, `Smax=1.523e-2 eV/Angstrom^3`, `Dmax=2.523`). These discrepancies are many orders of magnitude larger than admissible backend roundoff and change the source potential used by DATA6/pseudolabel/evaluation machinery.

The EXTRACT1-derived single-head `omat_pbe` training foundation is much closer under pure CuEq (`Emax=1.272e-6 eV`, `Fmax=1.669e-6 eV/Angstrom`, `Smax=3.772e-8 eV/Angstrom^3`, `Dmax=1.192e-6`, identical deterministic selection). This is retained as evidence motivating a later phase-separated acceleration experiment, but it does not authorize the current all-CuEq campaign contract. The full safe campaign must first complete under one backend authority.

Therefore the generated configuration is changed to:

```toml
[foundation]
family = "mace_mh_1"
head = "omat_pbe"

[acceleration]
backend = "e3nn"
only_cueq = false
require_available = true
```

`campaign_cli._config_template()` and `init --backend` now default to `e3nn`; `campaign.toml.example`, README, and the MLFF campaign user guide agree with this policy. `cueq` remains an explicit selectable backend and all ACCEL1 pure/hybrid qualification code is retained. No existing campaign TOML is rewritten automatically. A user who explicitly requests CuEq still receives the same fail-closed parity gate.

The next optimization experiment, only after a successful full e3nn campaign, is allowed to investigate a **phase-separated acceleration contract** in which source-foundation inference/DATA6/pseudolabel evaluation stays on e3nn while the EXTRACT1-derived training foundation is independently qualified for CuEq. That future experiment must use separate inference/training realization identities rather than relaxing the current parity thresholds.

## Post-major-revision MLFF optimization roadmap - exact scaling, DATA6 hardening, and phase-separated CuEq qualification

**Status:** revised on 2026-08-15 after SIZE-HALVE1 exposed a scientific flaw in PERF-P2's former four-smallest coverage truncation and after the locked foundation models were supplied for the final qualification campaign. PERF-BASE0/P0/P1 remain valid; PERF-P2 remains historical only. SIZE-FIDELITY1 is implemented but its real MACE/GPU survivor-recall run is now a **final-release blocker rather than an implementation blocker**. PERF-P2R and PERF-P3 therefore proceed against the parameterized full-ladder funnel, while `FINAL-GPU1` later executes all outstanding MLFF accelerator qualification in one release-matched package. The existing DATA6-MIC1 and TARGET-DATA2B-PERF1 hotfixes remain part of the starting baseline.

The purpose of this roadmap is to make the revised MLFF campaign scale cleanly from the present approximately 36,000-frame LTA development corpus to larger target corpora **without changing scientific selection, coverage, replay-retention, foundation identity, or validation semantics merely for speed**. The audit distinguishes exact execution optimization from storage-schema migration and from evidence-algorithm revision. Every gate below therefore carries an explicit equivalence burden.

### Optimization authority classes

Every performance change is assigned exactly one authority class:

- **Class E - execution-equivalent.** The scientific schema and persisted scientific authority are unchanged. For identical inputs, the same scientific content and content digest are required unless the pre-existing format itself contains execution-only metadata. Examples include precomputed FPS row norms, bounded cKDTree workers, and replacing an `O(K^2)` scratch matrix by an exact `O(K)` nearest-neighbor state.
- **Class S - storage/schema-equivalent.** The numerical scientific content and decision semantics must remain identical, but the evidence/storage schema is intentionally advanced. Historical records remain readable under their original meaning. TARGET-DATA2B native-array persistence is the principal example.
- **Class A - authority-algorithm revision with proven decision equivalence.** Evidence construction intentionally changes and receives a new authority schema/version, but the frozen scientific decision must remain equivalent on qualification corpora. Historical PERF-P2 was such an experiment under the former target-size rule.
- **Class C - scientific correction.** The scientific decision semantics intentionally change because the prior rule is no longer defensible. Decision equivalence is neither required nor claimed; migration, invalidation, and downstream authority updates are mandatory. SIZE-HALVE1 is Class C.

No gate may silently cross these classes. A Class C correction is never disguised as a performance win, and a performance optimization may not recreate superseded scientific semantics.

### Current hotspot and scaling model

The post-revision pipeline has three dominant performance regimes:

1. **CPU/reference-statistics preparation:** TARGET-DATA2B and TARGET-DATA2C repeatedly process tens of thousands of frames and many structural/target/residual feature families. Fixed reference-mass coverage deliberately causes the exact local-neighbor workload to grow with corpus size, and the new nested ladder may extend to 8,192 selected frames.
2. **GPU/autograd preparation:** DATA6 is dominated by MACE graph construction plus descriptor/energy/force/stress evaluation, CUDA memory capacity, and synchronous persistence boundaries.
3. **training/evaluation persistence:** TRAIN2 is primarily accelerator compute but also performs whole-model checkpoint/continuation persistence; EVAL2 already contains persistent graph/prediction caches and staged CPU/GPU execution, so its remaining optimization opportunities are secondary.

The principal audited hotspots are:

| Priority | Stage | Scaling or implementation issue | Planned remedy |
|---|---|---|---|
| P0 | TARGET-DATA2B persistence | large NumPy families expand into nested Python float/tuple/list/JSON objects | native-array v2 authority, sharded/mmap persistence, streamed hashing |
| P0 | TARGET-DATA2B local coverage | fixed-reference-mass exact kNN can return hundreds of neighbors per frame per family | preserve exact semantics; exploit exact uniform-weight order-statistic path; bounded parallelism; cautious backend qualification |
| P0 | TARGET-DATA2C exact FPS | nested exact FPS may run to `K=8192`, approximately `O(N K D)` | shared exact selector with immutable row norms and progressive state |
| P0 | DATA7 selected-set coverage | full `K x K` selected-distance scratch becomes 512 MiB at `K=8192` in FP64 | exact blockwise `O(K)` nearest-other-selected state |
| P1 | TARGET-DATA2C fused selector | wide FP64 matrix plus retained blocks/intermediates duplicates hundreds of MiB | one preallocated matrix, bounded mmap spill, fewer zero/temporary columns |
| P1 | TARGET-DATA2C rung scoring | nested prefixes are rescored largely from scratch | family-major progressive scoring and incremental nearest-selected state |
| P1 | DATA6 structural features | per-frame wrapper/object/temporary-array overhead | topology-static caches, direct numerical frame kernel, worker-local scratch |
| P1 | DATA6 MACE | graph-build/GPU/write stages are serialized and capacity calibration is workload-inaccurate | VRAM1 plus bounded CPU/GPU/I/O pipeline |
| P2R | corrected size funnel | full hard-coverage ladder plus 3/10/30 training increases candidate/preprocessing work relative to superseded lazy P2 | full-ladder state reuse, nested corpus/cache reuse, minimal epoch-3 target-only evaluation, exact pause/resume, stage-aware scheduling |
| P2 | TRAIN2 persistence | full model/EMA device-to-host clones and byte copies for every epoch | streamed tensor hashing; continuation-state deduplication only if restart equivalence is proven |
| P2 | FoundationTargetAudit | large per-atom error arrays are accumulated through Python lists then concatenated | exact one-allocation or temporary-mmap reduction |
| P3 | EVAL2 | repeated same-architecture model restoration remains after graph/prediction caching | optional validated model-shell/state-dict hot swapping |

The table is a prioritization aid only. Performance telemetry never enters scientific identity.

### Binding gate order

The normative order is:

```text
PERF-BASE0
  freeze exact numerical/decision/performance reference evidence
    |
    v
PERF-P0
  TARGET-DATA2B native/scalable exact authority
    |
    v
PERF-P1
  shared exact selection + progressive coverage engine
    |
    v
PERF-P2 (historical; superseded)
  lazy TARGET-DATA2C ladder authority v2
    |
    v
SIZE-HALVE1
  scientific correction: full hard-coverage ladder + 3/10/30 funnel
    |
    v
SIZE-FIDELITY1
  empirical calibration of epoch-3/10 survivor fidelity and coarse-monitor size
    |
    v
PERF-P2R
  optimized full-ladder successive-fidelity execution
    |
    v
PERF-P3
  CPU structural/reduction hardening + unified resource scopes
    |
    v
VRAM1 + PERF-P4
  DATA6 memory-planning correction + CPU/GPU/I/O pipeline overlap
    |
    v
E3NN-BASELINE
  one authoritative complete MH-1/omat_pbe/e3nn campaign
    |
    v
PERF-P5
  late TRAIN2/EVAL2 persistence/reuse hardening
    |
    v
CUEQ-DEP1
  exact accelerator runtime/dependency freeze
  (control plane implemented; positive accelerator record deferred to FINAL-GPU1)
    |
    v
CUEQ-PHASE1
  training-only CuEq qualification on EXTRACT1 single-head foundation
    |
    v
CUEQ-PHASE2 (optional)
  selected-head CuEq source-execution/DATA6 qualification
    |
    v
PERF-CERT1
  end-to-end scientific/performance certification and policy decision
```

The ordering is deliberate. The preparation-side asymptotic and memory issues should be fixed before the first full e3nn control campaign is frozen; otherwise the baseline would encode avoidable implementation bottlenecks. Accelerator experimentation remains after the authoritative e3nn baseline so backend changes are not confounded with preparation-engine changes.

## Gate PERF-BASE0 - frozen performance and numerical equivalence oracle

**Authority class:** baseline evidence; no scientific algorithm change.

PERF-BASE0 establishes the reference against which every later optimization is judged. Performance work may not rely only on wall-clock impressions or on the final selected frame count.

### PERF-BASE0 reference corpora

At minimum freeze:

1. a compact deterministic unit/regression corpus suitable for exact old-versus-new byte/numerical comparison;
2. adversarial geometry/statistics cases including duplicate feature points, exact/near distance ties, nonuniform correlation-unit weights, missing-family masks, and periodic-cell edge cases; and
3. one realistic large LTA preparation slice or complete development corpus representative of the approximately 36,408-frame workload.

Where a complete baseline operation would be unnecessarily expensive, PERF-BASE0 may freeze deterministic bounded family/stage subsets in addition to the complete campaign-level reference. The subset identity must be explicit.

### PERF-BASE0 scientific reference

Capture as applicable:

- TARGET-DATA2B family frame membership, scales, centers/quantiles, reference weights, local radii, authority digest, and family ordering;
- TARGET-DATA2C quota order, complete exact FPS prefix/order, each materialized rung membership, coverage/extent/stratum reports, survivor decisions, and authority digest;
- DATA6 structural vectors, foundation descriptors/predictions, difficulty values, recovery semantics, and downstream selection fingerprints;
- DATA7 production selection order and coverage reports;
- DATA8 training/replay bundle identities;
- representative TRAIN2 checkpoint/continuation identities; and
- EVAL2 selected-checkpoint/metric decisions where the baseline has reached those stages.

### PERF-BASE0 execution telemetry

Record, outside scientific digests:

- wall-clock and process CPU time;
- peak RSS and major temporary-array sizes;
- bytes read/written where measurable;
- frames/s, families/s, or selections/s appropriate to the stage;
- effective process/thread/cKDTree/BLAS/PyTorch worker counts;
- GPU peak allocated/reserved memory and driver-visible free memory for DATA6/TRAIN/EVAL; and
- OOM/backoff events.

PERF-BASE0 passes when the reference is reproducible enough to detect both numerical regressions and meaningful performance changes. Later Class E gates must compare against this oracle before their implementation becomes authoritative.

### PERF-BASE0 implementation record - 2026-08-15

**Implementation status (`0.20.178a0`): complete as bounded supplied-data authority.** `mdstats.training_data.performance_baseline` now provides versioned, fail-closed array, JSON, artifact, corpus, scientific-stage, execution-telemetry, record, comparison, persistence, rendering, and stage-meter contracts. Numerical arrays are authenticated as canonical little-endian C-order bytes. Orders, decisions, reports, policy identities, and availability declarations are canonical JSON references. Scientific and execution identities are deliberately separate: source release, timestamps, wall/process time, RSS, I/O, worker settings, thread-pool observations, host/cgroup identity, package versions, and accelerator observations do not enter the scientific digest.

The supplied-data oracle authenticates all input archives and processes the complete current target and replay materializations:

- **target:** 27 VASP XML sources, **37,633 frames**, **6,322,344 atoms**, and **966,777,484 extracted bytes**;
- **replay:** complete authoritative train/monitor/outlier splits, **12,000 frames** and **364,370 atoms**, with every supplied replay artifact byte-authenticated;
- **compact regression:** a deterministic six-point exact-reference corpus; and
- **adversarial regression:** duplicate points, exact and near ties, nonuniform correlation-unit weights, missing-family masks, and triclinic mixed-periodicity minimum-image geometry.

The realistic CPU scientific reference freezes eight exact TARGET-DATA2B-style target/stress/cell/mobile/framework/species-force family calculations totaling **263,398 family elements**, including balanced source-unit weights, robust scales, q01/q50/q99 extents, and the exact `beta = 1/128` leave-one-out local-radius rule. It also freezes an explicitly bounded exact deterministic incremental FPS prefix of **K = 1,024** over all **37,633 target frames**, with nested 128/256/512/1,024 coverage reports. The FPS record is a performance/equivalence fixture over the available label/cell/composition summary matrix; it is not promoted to production TARGET-DATA2C mandatory-quota or complete-ladder authority. No reference-radii target frame is subsampled and no approximate neighbor or selection algorithm is introduced.

Two independent complete runs on the available Intel Xeon Platinum 8573C container (8.0-core cgroup quota, 4 GiB memory limit, eight declared native threads) produced the identical scientific digest

`44a5aa8b492cece8d303f83a163ddbeee6d3a340932d4716c53b4ddf28a81e3c`.

The primary/reproducibility records are:

- `audits/analysis/mlff_perf_base0_lta_cloud_cpu_reference.json`;
- `benchmarks/mlff_perf_base0_lta_cloud_cpu_repro_run2_2026-08-15.json`;
- `audits/analysis/mlff_perf_base0_reproducibility_comparison.json`;
- `benchmarks/mlff_perf_base0_lta_cloud_cpu_2026-08-15.md`; and
- `benchmarks/mlff_perf_base0_reproducibility_2026-08-15.md`.

Observed same-host wall-time ranges are retained as the initial execution-noise envelope rather than collapsed into scientific authority:

| Stage | Complete supplied-data workload | Wall-time range | Throughput/effective-core range | Peak RSS range |
|---|---|---:|---:|---:|
| target XML ingestion | 37,633 target frames | 117.054--131.846 s | 285.431--321.500 frames/s; 1.010--1.021 effective cores | 527.14--527.31 MiB |
| replay ExtXYZ ingestion | 12,000 replay frames | 7.301--8.455 s | 1,419.339--1,643.672 frames/s; 1.008 effective cores | 527.16--527.34 MiB |
| exact local radii | 263,398 family elements | 5.518--6.265 s | 42,043.974--47,732.798 elements/s; 4.050--4.385 effective cores | 559.38--563.02 MiB |
| exact FPS and nested coverage | K = 1,024 over 37,633 frames | 6.019--9.600 s | 106.670--170.138 selections/s; 6.718--7.183 effective cores | 561.04--563.39 MiB |

The baseline identifies complete sequential ASE VASP-XML ingestion as the dominant current CPU cost. Later performance claims must compare exact scientific identity first and use repeated, matched-condition execution evidence; a single favorable wall time is insufficient.

No MACE-MH-1 checkpoint, authorizing GPU runtime, or complete campaign bundle was supplied. Production DATA6 model-derived families and inference telemetry, TARGET-DATA2C mandatory-quota/exhaustive-ladder authority, complete DATA7/DATA8 materialization, TRAIN2, EVAL2, GPU memory, and OOM behavior are therefore recorded as unavailable rather than inferred or fabricated. PERF-BASE0 closes only the exact supplied-data scope above.

This record was the input oracle for `PERF-P0`. The subsequently implemented native/scalable TARGET-DATA2B path in `0.20.179a0` preserves the oracle exactly and is documented below.

## Gate PERF-P0 - TARGET-DATA2B native and scalable exact authority

**Authority class:** primarily S for persistence; E for exact execution accelerations inside the unchanged coverage definition.

TARGET-DATA2B is the first major post-revision scaling boundary. The recent TARGET-DATA2B-PERF1 hotfix correctly adds bounded cKDTree parallelism and vectorized weighted-mass accumulation while preserving the current authority. PERF-P0 retains that improvement and removes the deeper object/persistence and repeated-statistics bottlenecks.

### PERF-P0.1 - native-array TARGET-DATA2B schema v2

Advance the persisted authority to a versioned native-array representation. Historical v1 tuple/JSON records remain readable with their original semantics.

The v2 family representation stores large numerical fields as authenticated native arrays rather than nested Python numeric objects. Conceptually:

```text
TargetCoverageReference.v2
  domain + policy metadata
  family table
    family identity / feature names / semantic role
    frame_indices.npy
    values.npy or sharded values
    scales.npy
    centers/quantiles.npy
    local_radii.npy
    weight_profile_id
  shared weight-profile table
  array manifests + hashes
```

Binding requirements:

1. large arrays are contiguous, dtype/shape-explicit, and persist through NPY-compatible or equivalent native binary payloads;
2. large arrays are hashed by canonical metadata plus streamed native bytes, never by expanding them through `.tolist()` or nested Python tuples solely for hashing;
3. persistence supports ZIP64/sharding and authenticated mmap restore when a payload exceeds the in-memory threshold;
4. shared reference-weight profiles are factored by domain + valid-frame-mask/correlation-unit identity rather than duplicated for every family when the weights are identical;
5. v1 -> v2 migration preserves numerical family values, scales, local radii, membership, and scientific policy exactly; and
6. execution-only settings such as worker count, chunk size, or mmap path are excluded from the scientific content digest.

The purpose is not compression at the expense of semantics. FP64/declared dtypes and exact stored values remain authoritative.

### PERF-P0.2 - exact uniform-weight fixed-mass radius fast path

The fixed-reference-mass definition remains unchanged. For families whose leave-one-out reference weights are mathematically uniform, the local radius required to reach the frozen mass fraction is exactly an order statistic of the non-self neighbor distances. Those families need not materialize and cumulatively sum a wide `N x k` weighted-neighbor result.

The implementation therefore classifies each weight profile:

```text
uniform under the authoritative leave-one-out rule
  -> exact required-neighbor-rank query

nonuniform correlation-unit weights
  -> exact weighted-mass neighbor accumulation
```

The optimization must preserve:

- the same beta/reference-mass target;
- the same leave-one-out denominator convention;
- duplicate-point and exact-distance-tie handling;
- the same local radius units and dtype; and
- the same downstream qualification decision.

Qualification compares the fast path against the pre-P0 weighted implementation on deterministic uniform-weight corpora, including duplicates and tie cases.

### PERF-P0.3 - shared weight-profile and valid-mask cache

Many coverage families operate over the same domain and valid-frame population. Cache the exact balanced reference weighting by a content identity derived from:

```text
label-domain/reference-domain identity
+ valid-frame membership/mask digest
+ correlation-unit policy identity
+ leave-one-out policy
```

The cache may supply frame indices, balanced weights, uniform/nonuniform classification, and reusable cumulative metadata. It is an execution cache; the resulting family authority must be identical to uncached construction.

### PERF-P0.4 - one stable ordering, many exact weighted statistics

Where a family/column needs several exact weighted quantiles or medians, perform one stable sort per scalar column and derive all required quantiles from the same cumulative reference mass. Avoid independent sorts for robust scale, center, extent bounds, and later fidelity statistics when they use the same authoritative weighting.

The ordering/reduction must preserve the existing weighted-quantile convention exactly, including stable tie behavior. Large all-column argsort matrices are not required; process columns or bounded blocks so the optimization does not trade CPU time for another excessive memory allocation.

### PERF-P0.5 - bulk family extraction

Replace repeated Python `uid -> frame_feature_vector -> tuple` construction with internal columnar/bulk interfaces where the underlying catalog is already array-like. The preferred internal contract is conceptually:

```text
values[N, D]
missing[N, D]
feature_names[D]
frame_indices[N]
```

Pair-geometry/raw structural rules that already share one distance calculation per center/neighbor species-pair group must retain that optimization. PERF-P0/P3 must **not** claim or implement a redundant "pair MIC reuse" change that the current source already provides.

### PERF-P0.6 - exact neighbor-backend qualification, not blind replacement

cKDTree remains the authoritative exact neighbor backend after TARGET-DATA2B-PERF1. Some high-dimensional families may eventually prune poorly. PERF-P0 may therefore include an execution benchmark hook comparing cKDTree with a bounded exact dense/blockwise distance kernel.

However, an alternative backend is not selected merely because it is faster. Because persisted local radii are floating-point authority, a new backend may become authoritative only after deterministic qualification establishes the declared numerical equivalence, including duplicate points and distance ties. Approximate nearest-neighbor libraries are outside this roadmap.

### PERF-P0 acceptance gate

PERF-P0 passes only when:

- v2 native persistence round-trips exactly and historical v1 remains readable;
- v1/v2 numerical content agrees under the migration oracle;
- the uniform-weight fast path agrees with the old exact weighted path under the declared numerical policy;
- cached versus uncached weight/statistics paths produce identical authority;
- no execution worker/chunk/mmap setting enters the scientific digest; and
- realistic-corpus peak RSS and wall time improve materially relative to PERF-BASE0.

### PERF-P0 implementation record - 2026-08-15

**Implementation status (`0.20.179a0`): complete for bounded supplied-data TARGET-DATA2B authority.** The scientific coverage version and policy remain unchanged. The gate advances only persistence and exact execution realization.

The public implementation provides:

- little-endian, C-contiguous, read-only `<i8`/`<f8` family arrays with streamed native-byte identities;
- content-addressed NPY shards, authenticated manifests and pointers, shared weight-profile storage, threshold-controlled read-only mmap restore, and fail-closed path/dtype/shape/byte/digest validation [21--23];
- exact historical v1 readability and elementwise v1-to-v2 migration reports;
- one stable ordering per scalar column for all required weighted quantiles, while retaining the explicit left-continuous weighted empirical convention because quantile definitions are not universal [24];
- exact balanced-weight profile reuse keyed by domain, frame membership, correlation units, weighting, and leave-one-out policy;
- exact uniform-weight fixed-mass rank dispatch with the old weighted cumulative-mass implementation retained as the oracle;
- profile-backed bulk family extraction into columnar value/missing arrays; and
- a bounded dense exact comparison backend while cKDTree remains production authority [25,26].

Campaign persistence now stores an authenticated native pointer rather than nested numerical JSON. Historical inline records migrate only after exact comparison and publication of a migration report. Worker count, query block size, cache enablement, mmap threshold/path, timing, and host observations remain outside the scientific digest.

The complete supplied-data benchmark uses all 27 target XML sources, **37,633 frames**, **6,322,344 atoms**, and eight exact families totaling **263,398 family elements**. All 48 numerical-array identities match the PERF-BASE0 `target_data2b_exact_radii` stage exactly. Five isolated pre-P0 and five PERF-P0 runs share scientific digest

`2f04aba96b876a10e62b7b0c22f26b544836005d11bc893177d4b29cbe4a3f82`.

| Path | Median wall | Observed range | Median process CPU | Median peak RSS |
|---|---:|---:|---:|---:|
| pre-P0 exact construction | 7.541 s | 6.826--9.926 s | 27.091 s | 329.47 MiB |
| PERF-P0 exact construction | 6.236 s | 5.818--8.253 s | 26.043 s | 328.50 MiB |

The matched median wall reduction is **17.30%**. The retained range records material scheduling noise rather than presenting one favorable run as authority.

| Persistence | Write wall | Read wall | Serialized bytes | Write RSS increment | Read RSS increment |
|---|---:|---:|---:|---:|---:|
| nested JSON v1 | 10.366 s | 14.382 s | 42,749,676 | 167.77 MiB | 189.35 MiB |
| native-array v2 | 0.184 s | 0.180 s | 17,912,666 | 0.12 MiB | 28.02 MiB |

At complete supplied-data scale, native v2 is **56.22x** faster to write, **79.70x** faster to read, and **58.10%** smaller. The v1/v2 migration report has no difference paths and both restored references have content digest

`4f46dfaa6c366ede1cd4d19cf5fb8be65cfe49067b5aff85d668e0078915f9b8`.

Authority and design detail are frozen in:

- `docs/history/mlff/retired_specs/mlff_perf_p0_native_target_coverage_spec.md`;
- `audits/analysis/mlff_perf_p0_lta_cloud_cpu_2026-08-15.json`;
- `audits/analysis/mlff_perf_p0_lta_cloud_cpu_2026-08-15.md`; and
- `release/MLFF_PERF_P0_QUALIFICATION_0.20.179a0.json`.

No MACE-MH-1 checkpoint, authorizing GPU runtime, or complete production campaign bundle was supplied. Production DATA6 model-derived families, complete TARGET-DATA2C/DATA7 authority, DATA8 materialization, TRAIN2/EVAL2 timing, GPU memory, and OOM evidence remain unavailable rather than inferred.

`PERF-P1` is implemented in `0.20.180a0`. Historical `PERF-P2` was implemented in `0.20.181a0`; SIZE-HALVE1 supersedes its generated-campaign truncation semantics in `0.20.182a0`. PERF-P2R CPU/control-plane execution is implemented in `0.20.184a0`; its accelerator qualification remains deferred to FINAL-GPU1. `PERF-P3` is implemented in `0.20.185a0`; VRAM1 + PERF-P4 CPU/control-plane execution is implemented in `0.20.186a0`; PERF-P5 is CPU-qualified in `0.20.187a0`; and CUEQ-DEP1's content-addressed runtime-freeze implementation is complete in `0.20.188a0`. **The positive CUEQ-DEP1 accelerator record and every later CuEq numerical/training/certification decision remain reserved for the consolidated `FINAL-GPU1` release handoff.**

## Gate PERF-P1 - shared exact selection and progressive coverage engine

**Authority class:** E unless a storage helper is explicitly versioned.

The same exact deterministic selection machinery is used by TARGET-DATA2C and DATA7. PERF-P1 consolidates the expensive primitives so they are optimized once and cannot diverge.

### PERF-P1.1 - immutable exact FPS workspace

Introduce a reusable exact-FPS state containing at minimum:

```text
row_norm_squared[N]
selected_mask or selected_rank[N]
min_squared_distance[N]
selected_order[K_so_far]
lexical_uid_rank[N]
```

The selector matrix does not change during a selection run, so row norms are computed once. Distance updates reuse:

$$
\|x-y\|^2 = \|x\|^2 + \|y\|^2 - 2x\cdot y.
$$

The implementation must retain the existing floating-point precision and deterministic tie tolerance. Avoiding vector-wide square roots is permitted only where the equivalent squared-distance comparison reproduces the exact current tolerance semantics; otherwise the current comparison is retained.

### PERF-P1.2 - quota stage hands state directly to FPS

Quota-first selection already computes novelty/min-distance information needed by subsequent FPS continuation. Do not discard and recompute it.

Centroid novelty also must not allocate a full `X - centroid` matrix when row norms and a matrix-vector product can compute the same squared distance exactly under the qualified numerical path.

Quota selection initializes `ExactFPSState`; FPS continues that same state to expose longer nested prefixes.

### PERF-P1.3 - preallocated fused TARGET-DATA2C selector matrix

Compute final selector width before construction, allocate the target FP64 matrix once, and fill column slices family by family. Release each temporary family block immediately.

If the matrix approaches the configured stage RAM budget, an authenticated temporary mmap may back the same FP64 matrix. The mmap location and chunking are execution details and cannot change scientific identity.

Presence/missing columns that are provably constant zero over the complete domain need not consume a physical all-zero column merely to preserve the metric. Their normalization contribution may be represented analytically only after an exact equivalence test proves that pair distances and selector ordering are unchanged.

### PERF-P1.4 - progressive multi-rung coverage scoring

Invert the current repeated-work structure. A coverage family should be loaded/scaled once, then scored progressively across the nested prefixes rather than reconstructed independently for every rung.

For nearest-selected coverage, retain a reference-sized state:

```text
nearest_selected_distance[N_reference]
```

When a rung adds selected points, update only against the newly added block:

$$
d_{new}(x)=\min\left(d_{old}(x), d(x,S_{added})\right).
$$

Likewise, maintain selected minima/maxima and reusable sorted scalar reference distributions for exact extent/Wasserstein/fidelity statistics. Bounded cKDTree/native workers used by scoring must consume the same stage CPU budget as other concurrent work rather than hard-code serial execution.

### PERF-P1.5 - DATA7 selected-neighbor coverage becomes O(K) persistent state

At `K=8192`, a dense FP64 `K x K` selected-distance matrix is 512 MiB. DATA7 only needs each selected point's nearest **other** selected point. Persist instead:

```text
selected_neighbor_min_squared[K]
```

When new selected points are appended, evaluate previous-new and new-new distances in bounded blocks and update the per-selected minimum. All required exact pair distances are still considered; only the unnecessary full matrix retention is removed.

The same incremental state should be reusable across nested DATA7 rungs.

### PERF-P1 acceptance gate

For every qualification corpus, require:

- identical quota-selected prefix/order;
- identical exact FPS order and selected membership through the largest tested rung;
- identical deterministic tie resolution;
- identical coverage/extent/stratum statistics under the existing numerical authority;
- identical Stage-A pass/fail decisions;
- identical DATA7 selected membership and coverage reports; and
- materially reduced wall time and/or peak memory on realistic wide-feature and `K`-large cases.

Where the existing schema is unchanged, Class E content digests must remain identical.

### PERF-P1 implementation record - 2026-08-15

**Implementation status (`0.20.180a0`): complete for bounded supplied-data and synthetic wide/K-large qualification.**

The exact engine is now shared rather than reconstructed by each selection stage:

- `ExactFPSState` owns immutable row norms, lexical UID ranks, selected mask/rank, minimum squared distances, and ordered selections. Quota-first TARGET-DATA2C initializes the same state continued by FPS. The distance update uses the standard squared Euclidean identity while retaining the historical FP64 tolerance and lexical tie policy. Farthest-first traversal follows the algorithmic pattern formalized by Gonzalez [27], but project authority remains the frozen pre-P1 deterministic order.
- Centroid novelty uses bounded `X-centroid` blocks rather than a full-domain temporary. The existing subtraction/reduction order is retained because an algebraically equivalent BLAS path is not presumed last-bit equivalent for deterministic ties.
- TARGET-DATA2C computes final fused width, allocates one FP64 selector matrix, and fills family slices directly. The former concatenate path remains a regression oracle.
- `score_target_nested_subsets_coverage` scales one family once, carries nearest-selected reference distances and selected extrema across nested rungs, and queries only newly added selected points. Exact `cKDTree.query(..., eps=0)` workers are supplied from the campaign CPU budget [28]. Existing one-dimensional Wasserstein statistics remain unchanged [29].
- DATA7 persists only `selected_neighbor_min_squared[K]`; bounded old-new and new-new pair blocks update both endpoints. Every required pair remains evaluated while persistent selected-neighbor state falls from $8K^2$ to $8K$ bytes.

The complete PERF-P0 native reference contains 37,633 target frames, eight coverage families, and a 37,633 x 50 fused selector matrix. Selector bytes, exact FPS order through K=1024, four nested coverage-report digests, worker-count invariance, regression TARGET-DATA2C ladder content, and regression DATA7 selection/coverage content are unchanged. The benchmark scientific digest is

`ff08ca4aee884f1aaf4bf1969454bb75fc9e875eb8c29d57c46fe0100dadb12e`.

| Qualification case | Legacy | PERF-P1 | Result |
|---|---:|---:|---:|
| full-reference exact FPS, K=1024 | 1.550 s | 0.657 s | 57.61% faster |
| wide exact FPS, 4000 x 128, K=512 | 0.182 s | 0.049 s | 73.25% faster |
| DATA7 K=8192 wall | 1.954 s | 0.506 s | 74.09% faster |
| DATA7 K=8192 peak RSS | 1149.89 MiB | 637.22 MiB | 44.58% lower |
| DATA7 K=8192 persistent state | 512 MiB | 64 KiB | 8192x smaller |

The progressive four-rung coverage path is exact but measured 0.709 s versus 0.643 s for repeated legacy scoring on this host, a 10.29% slowdown. The architecture records that result explicitly; PERF-P1 does not claim coverage-speed improvement. Its acceptance is supported by exactness plus the material FPS and DATA7 K-large wall/memory reductions.

Authority and evidence are frozen in:

- `docs/history/mlff/retired_specs/mlff_perf_p1_shared_exact_selection_spec.md`;
- `audits/analysis/mlff_perf_p1_lta_cloud_cpu_2026-08-15.{json,md}`; and
- `release/MLFF_PERF_P1_QUALIFICATION_0.20.180a0.json`.

Historical `PERF-P2` remains archived at `0.20.181a0`. SIZE-HALVE1 is the current Class-C scientific correction in `0.20.182a0`; SIZE-FIDELITY1 authority is implemented in `0.20.183a0`. Revisions 50--51 change qualification scheduling and implementation status: the real MACE/GPU calibration remains mandatory before final production release, but it no longer blocks CPU/control-plane development. PERF-P2R is implementation-qualified in `0.20.184a0`; `FINAL-GPU1` owns its deferred accelerator qualification.

## Historical gate PERF-P2 - lazy TARGET-DATA2C ladder authority v2 (superseded)

**Historical implementation:** `0.20.181a0`.  
**Current status:** superseded for generated campaigns by `SIZE-HALVE1`.

PERF-P2 v2 stopped TARGET-DATA2C after enough coverage-qualified rungs existed to prove the old
four-smallest Stage-A shortlist. The implementation and its bounded benchmark remain valid historical
evidence for that algorithm: on the forced early-stop fixture, median wall time fell from 7.867 s to
1.556 s (80.23%) while preserving the then-defined Stage-A survivor decision.

The scientific premise is no longer current. Coverage is now hard admission only, so larger
coverage-qualified rungs remain candidates for the epoch-3 learning screen. A v2 intentional absence
therefore cannot be interpreted as current evidence that a larger target size is unnecessary.

Historical v1/v2 ladder records remain inspectable where supported. Current generated campaigns require
TARGET-DATA2C v3 and rebuild stale v1/v2 campaign authority.

## Gate SIZE-HALVE1 - hard-coverage plus 3/10/30 target-size correction

**Authority class:** C - scientific correction.  
**Implementation status (`0.20.182a0`): structurally complete; production coarse-fidelity certification pending SIZE-FIDELITY1.**

SIZE-HALVE1 intentionally changes target-size decisions and is therefore **not** an execution-equivalent,
storage-equivalent, or decision-equivalent performance optimization. It corrects the scientific authority:

```text
coverage: all materializable rungs -> all hard qualifiers
3 epochs target-only: all qualifiers -> <=4
10 epochs target-first: <=4 -> 2
30 epochs full qualification: 2 -> 1
```

The gate advances:

- TARGET-DATA2C to v3 complete-ladder authority;
- TARGET-DATA2D to v2 3/10/30 convergence authority;
- target-size training evidence to v3 with checkpoint/optimizer/RNG continuation ancestry;
- TARGET-DATA2E to v2 full-funnel provenance; and
- EVAL2 with a fixed common `size_development_coarse` target-only role.

Early epoch-3/10 practical-equivalence ordering preserves the largest hard-coverage boundary **within its
equivalence band** so a tied boundary is not discarded before bounded-ladder convergence can be tested.
The boundary receives no protection when materially worse. Final epoch-30 equivalence again prefers the
smaller data set.

The detailed scientific contract and migration rules are frozen in the [SIZE-HALVE1 normative specification](docs/specs/training_data/mlff_size_halve1_target_size_revision_spec.md).

## Gate SIZE-FIDELITY1 - empirical coarse-screen calibration

**Authority type:** scientific qualification of SIZE-HALVE1; no performance credit.  
**Implementation status (`0.20.183a0`): calibration authority and execution plan implemented; authorizing MACE/GPU evidence pending.**

The 3-epoch screen is useful only if low-fidelity ranking preserves the candidates that matter at the
30-epoch target decision. SIZE-FIDELITY1 therefore runs **every hard-coverage-qualified size to 30 epochs**
for at least three frozen optimizer seeds. Halving is disabled during calibration. Candidate 3-, 4-, and
5-epoch screens are replayed retrospectively from checkpoints on those same uninterrupted trajectories.

The default calibration matrix is:

```text
optimizer seeds:                 1, 2, 3
candidate coarse endpoints:      3, 4, 5 epochs
coarse monitor candidates:       128, 256, 512, 1024 configurations
coarse equivalence candidates:   1, 2, 4 meV/A
short/full endpoints:            10 / 30 epochs
```

The first coarse endpoint and first equivalence width are bound to the current production defaults. Later
endpoints and wider early equivalence bands are fallback hypotheses tested in the same exhaustive
calibration campaign; they are not independently restarted schedules.

### SIZE-FIDELITY1.1 - one inference authority, many monitor views

Every calibration checkpoint is evaluated once on the complete leakage-safe size-development role. The
128/256/512/1024 coarse-monitor scores are then reduced from deterministic frame subsets of those same
authenticated per-frame predictions. The gate explicitly forbids purchasing a separate MACE inference
pass for every monitor size.

For $N_K$ hard-coverage sizes and $N_s$ calibration seeds, v1 purchases

$$
N_{\mathrm{train}}=N_KN_s
$$

uninterrupted 30-epoch trajectories and

$$
N_{\mathrm{infer}}=5N_KN_s
$$

full-role inference endpoints at epochs 3, 4, 5, 10, and 30. Monitor-size calibration does not multiply
the inference count.

### SIZE-FIDELITY1.2 - hard survivor-recall authority

For each seed, the 30-epoch full-development target ranking defines the retrospective target finalists
$F_s$, the first two valid sizes under the final practical-equivalence rule. A candidate coarse setting
passes only when, for **every** frozen seed:

1. its monitor-based coarse promotion set equals the promotion set from the full development role;
2. both members of $F_s$ survive the coarse top-four screen;
3. both members of $F_s$ survive the epoch-10 top-two screen;
4. the eventual target winner survives both screens;
5. an eventual largest-size boundary finalist is never lost; and
6. checkpoint/run identities prove one uninterrupted trajectory per seed and size.

Requiring both eventual finalists at epoch 10 is intentional. Preserving only the target winner is not
sufficient because later replay or physical hard gates can disqualify that first finalist; the scientifically
relevant alternative must still exist.

The hard default is therefore

$$
R_{\mathrm{coarse}}=R_{10}=1.
$$

Mean Spearman rank correlation, seed-to-seed survivor stability, and winner recall are recorded as
diagnostics. Rank correlation cannot compensate for one false elimination.

### SIZE-FIDELITY1.3 - deterministic recommendation

Among settings that satisfy every hard requirement, choose the earliest faithful coarse endpoint, then
the smallest monitor with exact promotion-set equivalence, then the smallest tested early equivalence
width at or above the current production default. No passing setting means the **final production release** fails closed.
PERF-P2R implementation may continue only because it is required to support the whole calibration grid and cannot
freeze a GPU-derived default before FINAL-GPU1. Corrective scientific options remain a later coarse endpoint, larger
monitor, wider early equivalence band, or a newly versioned funnel - never coverage-based truncation.

The implemented authority is `mdstats.size-fidelity1.coarse-screen-calibration.2026-08.v1` in
`mdstats.training_data.size_fidelity`. It provides authenticated calibration-policy, execution-plan, metric,
candidate-assessment, and qualification-report records. The detailed contract is frozen in the
[SIZE-FIDELITY1 normative specification](docs/specs/training_data/mlff_size_fidelity1_coarse_screen_calibration_spec.md).

The supplied foundation checkpoints are now present and match the previously locked byte identities. The
current development host still has CPU-only PyTorch and no CuEquivariance/CUDA runtime. `0.20.184a0`
therefore keeps SIZE-FIDELITY1 **scientifically open but implementation-complete**. The actual 30-epoch
survivor-recall result is deferred to `FINAL-GPU1` and remains a hard release blocker.

## Gate FINAL-GPU1 - deferred final-release MLFF accelerator qualification

**Authority class:** qualification scheduling/release evidence; no scientific credit by itself.  
**Implementation status (`0.20.184a0`): policy, locked-model manifest, and one-shot preflight implemented; final CUDA/CuEq execution deferred by design.**

The development workflow performs no intermediate GPU qualification handoff. CPU/e3nn reference tests,
exact scientific-identity tests, serialization tests, and CPU performance gates continue normally. Any
accelerator-dependent gate may reach implementation-complete state, but its accelerator qualification
state remains `pending` until the final release package is frozen.

The locked external foundation inputs are listed below. SHA-256 values are wrapped as two 32-character blocks for page safety; concatenate the blocks without whitespace.

**MACE-MH-1** - required head `omat_pbe`

```text
ec00a2705854622fbbd898ccfb770107
2fcd674709102d009fb919c1b8cc5dde
```

**MACE-MPA-0-medium** - required head `default`

```text
75428afe3a1d7d8062e19bcaabd5c43
3623cabf308242ec9fb493e38604fb638
```

`FINAL-GPU1` consolidates real CuEq activation/parity, DATA6 descriptor/selection parity, bounded CuEq
training realization, generated-default MH-1 certification, SIZE-FIDELITY1 exhaustive calibration, and
PERF-P2R whole-funnel GPU/VRAM performance authority. ML-IAP/LAMMPS deployment parity is packaged beside
this wave but remains a separate capability because it additionally requires an ML-IAP-enabled `lmp`.

For a GPU-dependent gate $g$, implementation and qualification are distinct:

$$
I(g) \in \{\mathrm{planned},\mathrm{implemented}\},
\qquad
Q(g) \in \{\mathrm{pending},\mathrm{pass},\mathrm{fail}\}.
$$

Downstream implementation may consume a stable parameterized interface when $I(g)=\mathrm{implemented}$.
Final production release may consume an accelerator result only when the required $Q(g)=\mathrm{pass}$.
`pending` never implies success and may not authorize a GPU-derived scientific default or speed claim.

The one-shot preflight is `tools/run_mlff_final_gpu_qualification.py`; the normative contract is
[FINAL-GPU1](docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md).

## Gate PERF-P2R - optimized full-ladder successive-fidelity execution

**Authority class:** E by default; S only when an explicitly versioned cache/storage helper changes.  
**Implementation status:** CPU/control-plane implementation qualified in `0.20.184a0`; accelerator/scientific runtime qualification deferred to FINAL-GPU1.

PERF-P2R may now be implemented before SIZE-FIDELITY1's accelerator run because the scientific controls are
already explicit parameters. It must support the complete calibration grid rather than assume that 3 epochs,
256 monitor configurations, or a 1 meV/A coarse equivalence width will survive final calibration. It replaces
the obsolete goal of stopping the coverage ladder with a performance plan tailored to
the corrected 3/10/30 funnel. The optimization target is **total time-to-qualified target size**, while
retaining all hard-coverage candidates until learning evidence eliminates them.

Revision 51 realizes that interface. `PerfP2RParameterGrid` defines the full 3/4/5-epoch, 128/256/512/1024-monitor, 1/2/4-meV/A, and 3--7-admitted-size compatibility surface. `build_perf_p2r_stage_plan()` is the single campaign work-authorizing stage translator. DATA8 fixed files use an authenticated content-addressed cache, and DATA7/DATA8 may share one frame-array index under an unchanged frame-catalog authority. The cache and index are execution-only; cache hit and miss remain subject to exact scientific artifact identity.

### PERF-P2R.1 - exact full-ladder coverage reuse

Reuse the PERF-P1 exact FPS workspace through the largest globally materializable rung. Coverage families
are loaded/scaled once; nearest-selected, extent, and other exact progressive state is carried across all
nested rungs. Proven monotonicity may avoid redundant arithmetic or permit cached pass certification, but
may never omit a candidate membership needed by the epoch-3 screen.

### PERF-P2R.2 - nested corpus and preprocessing reuse

Where scientifically safe, materialize the largest authorized nested target corpus once and represent
smaller rungs by authenticated prefix/index manifests rather than duplicated frame bytes. Reuse immutable
frame-level graph, neighbor, descriptor, and preprocessing artifacts across sizes when their scientific
preprocessing policy and frame identity are identical.

Cache location, mmap path, process/thread geometry, chunk size, and eviction policy remain execution-only.
A cache hit and cache miss must yield identical scientific input bytes/arrays to TRAIN2.

### PERF-P2R.3 - minimal epoch-3 evaluation path

The epoch-3 screen purchases only what can affect that decision:

- one endpoint evaluation per hard-coverage-qualified candidate;
- one fixed common target-only monitor, default 256 configurations;
- no replay inference;
- no checkpoint rescue search;
- no paired-bootstrap checkpoint selection; and
- no PES/relaxation/dynamics verification.

The prepared monitor and its graph/cache may be reused across every candidate because the role is common.
Where exact EVAL2 output identity is proven, same-process boundary evaluation may consume the already-resident model and prepared monitor, avoiding checkpoint reload while emitting the same separate scientific authority.

### PERF-P2R.4 - exact pause/resume without repeated prefixes

A target-size candidate is initialized once. Persist exact epoch-3 and epoch-10 boundary model/checkpoint,
optimizer/scheduler, and RNG authority. Survivors continue the same run to the next boundary. No candidate
may repay the first three or ten epochs because the orchestration layer restarted it as a new schedule.

After elimination evidence is durably frozen, transient non-survivor checkpoints may be reclaimed under
the storage-retention policy. The immutable evidence/digests required to audit elimination remain.
Continuation qualification must also cover DataLoader sampler/worker state or prove deterministic epoch-boundary reconstruction. Extra recovery checkpoints between scientific boundaries are execution-only and may be thinned when restart safety remains bounded; the 3/10/30 authority checkpoints are mandatory.

### PERF-P2R.5 - stage-aware resource scheduling

The scheduler launches only work authorized by the current funnel state.

- **Single GPU:** deterministic work-conserving dispatch, cache-aware candidate ordering, bounded CPU
  preprocessing, and prompt release of non-survivor accelerator/storage state.
- **Multiple GPUs:** peers within one stage may execute concurrently only under an explicit GPU/CPU/I/O
  budget. Oversubscribing DataLoaders, BLAS/OpenMP pools, graph builders, or shared storage is prohibited.
- Performance evidence records accelerator/host class so heterogeneous hardware is not compared as if it
  were one matched run.

### PERF-P2R.6 - whole-funnel performance authority

Qualification measures the complete path from hard-coverage admission through the selected 30-epoch
finalist. At minimum record:

- total and per-stage wall/process time;
- per-candidate optimizer updates and structures presented;
- GPU utilization and peak/reserved VRAM;
- host preprocessing time and peak RSS;
- disk/network I/O and checkpoint bytes;
- cache hit/miss and graph/preprocessing reuse;
- pause/resume overhead; and
- scientific identity of uninterrupted versus resumed endpoints.

Microbenchmarks remain diagnostic; they do not replace the whole-funnel authority.

### PERF-P2R exposure envelope

For hard-coverage qualifiers $A$, epoch-3 survivors $S_4$, and epoch-10 finalists $S_2$, a useful target
structure-epoch exposure proxy is

$$
W = 3\sum_{i\in A}K_i
  + 7\sum_{i\in S_4}K_i
  + 20\sum_{i\in S_2}K_i.
$$

Training all admissible candidates to 30 epochs would expose

$$
W_{\mathrm{full}} = 30\sum_{i\in A}K_i.
$$

For all seven default rungs, $\sum K_i=16256$. If the four largest and then the two largest survive,
$W=402048$ versus $W_{\mathrm{full}}=487680$, a 17.56% reduction. If the four smallest and then the two
smallest survive, $W=69888$, an 85.67% reduction. These are exposure bounds, not wall-time predictions;
GPU occupancy, batch geometry, replay, preprocessing, and I/O can materially change measured runtime.

### PERF-P2R acceptance

PERF-P2R now has separate implementation and final-qualification acceptance. CPU/control-plane implementation is qualified when:

1. cache miss, cache population, and cache hit reproduce the exact DATA8 authority;
2. one parameterized stage planner covers coarse endpoints 3, 4, and 5 and admitted ladder widths 3 through 7;
3. coarse-stage authorization is target-only and forbids replay/physical work;
4. promoted short/final stages require continuation from the preceding scientific boundary;
5. exact exposure accounting demonstrates no repaid training prefix; and
6. cache/index location and lifecycle remain execution-only.

FINAL-GPU1 must still prove:

1. identical TARGET-DATA2C v3 membership and hard-coverage evidence on the release-matched campaign;
2. calibrated coarse/epoch-10 survivor decisions and final selected/nonconverged outcome;
3. resumed versus uninterrupted checkpoint/optimizer/scheduler/RNG/sampler ancestry;
4. identical target/replay/physical evidence at every purchased endpoint;
5. bounded host/GPU/I/O resource scopes; and
6. measured whole-funnel operational benefit on the authorizing MACE/GPU runtime.

Thus `I(PERF-P2R)=implemented` in `0.20.184a0` while `Q(PERF-P2R)=pending` until FINAL-GPU1. No GPU funnel speed, calibrated coarse default, or survivor-fidelity claim is inferred from CPU microbenchmarks. PERF-P3 may proceed against this stable parameterized execution interface.


## Gate PERF-P3 - CPU structural and reduction hardening

**Authority class:** E.

PERF-P3 addresses remaining per-frame Python/allocation overhead after the large DATA2B/DATA2C scaling problems are removed.

### PERF-P3.1 - direct local-structure frame kernel

The public `compute_local_structure_features()` API remains available, but high-throughput DATA6 structural selection may call an internal numerical kernel directly with:

```text
atomic_numbers/topology identity
fractional or Cartesian positions
cell + PBC
precomputed topology workspace
worker-local scratch workspace
```

This avoids constructing a one-frame `AtomisticFrameCollection` and associated Python wrapper objects for every reference frame.

### PERF-P3.2 - topology-static caches and worker-local scratch

For runs with fixed atomic identities/topology, precompute once per topology:

- species/group row maps;
- pair radii and species-pair lookup tables;
- feature aggregation layout;
- invariant rule/group indices; and
- any constant mask/normalization structures.

Each structural worker may retain bounded reusable scratch, but measured PERF-P3 qualification retains **only wrapped fractional-coordinate scratch**. Dense reusable pair/radial scratch was rejected because it increased RSS and reduced throughput on the bounded LTA-like workload. A chunked radial reduction was also rejected after changing FP64 radial values at approximately $10^{-16}$ to $8.9\times10^{-16}$; Class-E byte identity takes precedence over a numerically small difference.

The qualified topology workspace precomputes immutable covalent radii, species indicators, pair radii, center/upper-triangle indices, and fallback-radius metadata. These caches and all scratch are execution-only.

### PERF-P3.3 - preserve already-correct pair-geometry reuse

The current raw pair-geometry path already computes the distance matrix once for rules sharing a center/neighbor species-pair group. This optimization is retained. PERF-P3 specifically does **not** introduce a second redundant pair-MIC cache or claim that pair-rule MIC repetition remains a hotspot.

Likewise, dense structural feature definitions are not replaced by sparse cutoffs merely for speed. A cutoff/sparse representation would be a scientific feature revision and is outside this execution-equivalent gate.

### PERF-P3.4 - FoundationTargetAudit temporary-memory hardening

Where exact per-atom force-vector/component error arrays are currently accumulated through Python lists and concatenated, determine the final required length and fill one exact native array allocation when practical. If the required allocation exceeds a configurable RAM threshold, use a temporary mmap with identical dtype/order. Exact quantile and audit semantics remain unchanged.

### PERF-P3.5 - unified stage-local resource scopes

Parallel layers must consume one declared stage budget rather than multiply independently. The execution controller/logging should distinguish at least:

- Python process/family concurrency;
- structural worker count;
- cKDTree native worker count;
- BLAS/OpenMP thread count;
- PyTorch CPU/DataLoader worker count; and
- GPU-job concurrency.

Representative policy:

```text
TARGET-DATA2B:
  family concurrency x tree workers <= stage CPU budget
  BLAS threads bounded, often 1 during tree-heavy work

TARGET-DATA2C exact FPS:
  Python concurrency = 1
  BLAS threads autotuned/bounded for matrix-vector bandwidth

DATA6:
  bounded CPU graph producer(s)
  one authoritative GPU inference stream per model/device
  one bounded persistence consumer
```

Use threadpool scoping where practical. Effective execution counts are telemetry only and cannot enter scientific content digests.

### PERF-P3 implementation record (`0.20.185a0`)

The qualified implementation adds an internal direct frame-array kernel while keeping the public `compute_local_structure_features()` API intact. DATA6 builds one immutable topology workspace per fixed-topology run and uses worker-local coordinate scratch. The direct path is bitwise-equivalent to the public path on regression authorities. The batched two-operand angular contraction uses the direct `einsum` path rather than repeatedly planning an equivalent contraction order.

FOUNDATION-AUDIT1 now determines exact final force-tail lengths and fills one vector-error array and one component-absolute-error array. When the execution-only threshold is exceeded, the same arrays are backed by a temporary mmap. The generated configuration exposes `performance.foundation_audit_temporary_ram_mib = 512`; nonpositive values fail closed.

`StageResourceScope` provides one conservative nested CPU admission bound:

$$
T_{\mathrm{est}}=W_{\mathrm{py}}\max\!\left(W_{\mathrm{struct}}T_{\mathrm{BLAS}},W_{\mathrm{tree}},W_{\mathrm{torch}},1\right)\le T_{\mathrm{budget}}.
$$

On the bounded cloud host, the 168-atom/300-frame LTA-like per-worker structural fixture improves median wall time from 3.458792 s to 3.202054 s (7.42%) with exact digest `5786409f8f622b3e2d1183bcca9ef9859e3cfd7717970339f421d4f630d6ac4c`. The 900,000-atom FOUNDATION-AUDIT1 fixture reduces peak RSS from 346.18 MiB to 318.41 MiB (8.02%) with exact digest `a618301c7f8dad6f5cd8cfec4d39edea9303b5c2f1c52bf46b81507677808f9f`. Audit preallocation is classified as memory hardening, not a speedup. GPU qualification remains deferred to FINAL-GPU1.

### PERF-P3 acceptance gate

Require exact feature/audit equivalence to PERF-BASE0, stable worker-count invariance, fail-closed nested-resource admission, and measured CPU throughput and/or peak-RSS benefit on bounded realistic workloads. PERF-P3 CPU qualification is satisfied in `0.20.185a0`; accelerator qualification remains outside this gate.

## Gate VRAM1 + PERF-P4 - DATA6 memory-planning correction and overlapped execution

**Authority class:** S for `MaceBatchCapacityCalibration.v2`; E for batching/pipeline execution.

The earlier post-CERT audit identified a real DATA6 capacity-planning mismatch. Calibration probes descriptor-only `get_descriptors_batch()` while overlapping production frames may run derivative-bearing `evaluate_batch()` with energy, force, stress, and descriptors. Successful probes can leave CUDA high-water cache behind, and a calibrated cap can be trusted without a fresh post-calibration live-VRAM clamp. Runtime OOM backoff is not durable.

VRAM1 corrects the evidence and safety contract; PERF-P4 then overlaps independent CPU/GPU/I/O work without changing scientific results.

### VRAM1 architecture requirements

1. **Advance capacity evidence to `MaceBatchCapacityCalibration.v2`.** Historical v1 remains readable only with its original descriptor-only semantics.
2. **Make workload mode explicit:** at minimum `descriptor_only`, `prediction_only`, and derivative-bearing `combined_evaluate`. The real overlapping DATA6 workload uses the appropriate authoritative mode.
3. **Measure absolute and incremental CUDA pressure:** baseline/peak `memory_allocated`, baseline/peak `memory_reserved`, and driver-visible free/total memory from `torch.cuda.mem_get_info()` before/after probes.
4. **Deterministically clean calibration state:** release probe-local graph/output objects, synchronize CUDA, collect Python garbage where required, and empty the caching allocator after one-time calibration before production begins. Do not routinely empty the cache between normal production batches.
5. **Use a deterministic stress-oriented calibration corpus:** not merely the first few frames. Include expensive graph geometries, large atom counts, and high edge counts where those vary. Bind corpus/frame identities into v2 evidence.
6. **Remeasure and re-clamp after cleanup:** a prior calibrated cap never exempts execution from the current free-VRAM/headroom budget.
7. **Use absolute + fractional headroom:** the stricter configured limit wins. A 24-GiB-class generated policy may target roughly 75-80% effective occupancy and/or approximately 4 GiB reserve, but these are execution defaults rather than scientific constants.
8. **Make batch choice throughput-aware:** among safe probe sizes, choose the smallest batch within a small declared tolerance (generated default 5%) of the maximum measured throughput.
9. **Persist OOM-derived safe caps:** visibly report `old_batch -> new_batch`, clear failed transient allocations safely, retry, and persist the learned runtime cap keyed by model/inference/device/dtype/workload/calibration identity. Changed identity invalidates the cap.
10. **Keep batching scientifically inert:** batch size, allocator state, and headroom policy may change throughput but not descriptors, predictions, target authority, or selection decisions beyond the already-declared model numerical tolerance.

### PERF-P4 bounded CPU/GPU/I/O pipeline

After VRAM1 establishes safe memory bounds, permit a bounded pipeline:

```text
CPU graph producer for batch n+1
             |
             v
GPU inference for batch n
             |
             v
CPU conversion/journal/shard persistence for batch n-1
```

Requirements:

- queues are explicitly bounded and their worst-case host/device memory is included in resource admission;
- graph order and result order remain deterministic by frame identity;
- the append-only recovery journal remains the authoritative commit boundary;
- asynchronous/background persistence may not acknowledge a frame before durable payload/journal ordering satisfies the existing recovery contract;
- pinned memory/nonblocking transfers are used only when benchmarked beneficially and memory-accounted;
- production may fall back to synchronous execution without changing scientific evidence; and
- graph construction for the next batch may overlap current GPU evaluation only when no mutable model/provider state is shared unsafely.

### VRAM1/PERF-P4 acceptance gate

Require:

- calibration v2 round-trip and v1 compatibility;
- forced batch-1, automatically calibrated, and deliberate OOM-backoff executions to agree scientifically;
- MPA-0/e3nn and MH-1/e3nn regression coverage;
- restart after an OOM-derived cap to reuse the safe cap only under matching identity;
- bounded peak VRAM with declared reserve on the qualification GPU; and
- measurable throughput improvement or unchanged throughput at materially lower memory pressure.

### VRAM1/PERF-P4 implementation record (`0.20.186a0`)

The control plane now uses `MaceBatchCapacityCalibration.v2`. Each record binds the descriptor signature, checkpoint identity, explicit workload mode, deterministic stress-frame identities, requested/probed/successful batch sizes, per-probe throughput, allocator `allocated`/`reserved` baselines and peaks, driver-visible free/total memory, absolute reserve, fractional occupancy limit, and post-cleanup memory state. Serialized host-memory admission additionally records conservative graph, descriptor, and prediction bytes per structure. Historical v1 evidence remains readable but retains descriptor-only semantics and cannot silently become combined-workload authority.

The safe-batch decision is

$$
B^* = \min\left\{B \in \mathcal{S}:\; q(B) \ge (1-\epsilon)\max_{b\in\mathcal{S}}q(b)\right\},
$$

where $q(B)$ is measured structures per second, $\epsilon=0.05$ by generated default, and $\mathcal{S}$ contains only successful probes satisfying both allocator/device-budget and absolute/fractional headroom. After one calibration cleanup, execution re-reads live device state and clamps $B^*$ again. An OOM during production halves the active batch without advancing frame order, persists the learned safe/rejected pair, and reuses it only under the same checkpoint/policy/device/dtype/workload/calibration identity.

PERF-P4 separates native MACE CPU graph preparation from device evaluation, permitting one prepared batch to be produced while the preceding batch is evaluated. Descriptor/prediction shard writes can run on one bounded persistence executor. Results are committed in deterministic frame order only after payload persistence completes; the existing append-only journal and final compaction remain recovery authority. Queue admission counts one active inference batch, one prepared graph batch, and the configured persistence queue, with graph + descriptor + prediction host footprints. Synchronous execution remains scientifically identical and is the fallback.

The supplied MH-1/`omat_pbe` and MPA-0-medium/`default` CPU/e3nn prepared/direct combined-evaluation paths are byte-identical on the locked regression structures. The bounded 44-frame CPU control-plane fixture also produces one identical scientific signature in synchronous and pipelined modes. On this CPU-only host the pipeline is slower, so no pipeline speedup is claimed and pinned/nonblocking transfer is not enabled as authority. CUDA peak/reserve, OOM capacity, transfer overlap, and end-to-end throughput acceptance remain explicitly deferred to `FINAL-GPU1`.

The implementation follows PyTorch's distinction between tensor allocation and caching-allocator reservation, uses `torch.cuda.mem_get_info()` for driver-visible free/total memory, and invokes `empty_cache()` only at the declared one-time calibration/OOM cleanup boundaries rather than each normal batch.[^vram-pytorch-cuda] PyTorch's transfer guidance notes that page-locked memory and nonblocking copies are workload dependent and should be benchmarked rather than assumed beneficial; this is why PERF-P4 leaves pinning disabled until the final accelerator qualification.[^vram-pytorch-pin] The bounded producer/persistence executors use Python's `ThreadPoolExecutor` interface.[^vram-python-futures]

[^vram-pytorch-cuda]: PyTorch, CUDA memory APIs: <https://docs.pytorch.org/docs/stable/cuda.html>; `mem_get_info`: <https://docs.pytorch.org/docs/stable/generated/torch.cuda.memory.mem_get_info.html>; `empty_cache`: <https://docs.pytorch.org/docs/main/generated/torch.cuda.memory.empty_cache.html>.
[^vram-pytorch-pin]: PyTorch, *A guide on good usage of `non_blocking` and `pin_memory()`*: <https://docs.pytorch.org/tutorials/intermediate/pinmem_nonblock.html>.
[^vram-python-futures]: Python documentation, `concurrent.futures`: <https://docs.python.org/3/library/concurrent.futures.html>.

### Deferred accelerator acceptance

VRAM1/PERF-P4 is **implemented and CPU/control-plane qualified**, not accelerator-qualified. `FINAL-GPU1` must still establish bounded peak VRAM under the declared reserve, successful calibrated and forced-OOM agreement on CUDA, and a pipeline throughput/memory-pressure result on the final release-matched workstation. PERF-P5 has subsequently completed the remaining late CPU/control-plane persistence hardening. E3NN-BASELINE and VRAM1/PERF-P4 accelerator evidence remain final-release obligations.

## Gate E3NN-BASELINE - authoritative complete MH-1 control campaign

After PERF-P0 through PERF-P5 are implemented and the final release-matched accelerator runtime is available, execute and freeze one complete production-representative campaign with:

```toml
[foundation]
family = "mace_mh_1"
head = "omat_pbe"

[acceleration]
backend = "e3nn"
only_cueq = false
require_available = true
```

This baseline is the scientific and performance control for later accelerator experiments. It must complete preparation, TARGET-DATA2 authority/selection, DATA6/DATA7/DATA8, TRAIN2, EVAL2, target-head extraction/materialization, and available deployment/physical verification under the normal e3nn source-foundation execution authority.

Freeze:

- exact source-foundation/checkpoint/head identity;
- final preparation/selection authorities;
- selected checkpoint and target-head artifacts;
- target/replay/evaluation metrics and hard-gate decisions;
- end-to-end wall time and stage telemetry; and
- physical/deployment verification outcomes.

A failed scientific campaign is not a valid accelerator baseline even if its performance telemetry is useful diagnostically.

## Gate PERF-P5 - late TRAIN2/EVAL2 persistence and reuse hardening

**Authority class:** E unless continuation/evidence storage is explicitly versioned.

**Implementation status (`0.20.187a0`): CPU/control-plane qualified.** GPU-side persistence overlap or accelerator model-shell benefit remains a `FINAL-GPU1` measurement, not an intermediate development requirement.

### PERF-P5.1 - TRAIN2/STOR2 streamed tensor hashing

TRAIN2 live/EMA-state hashing and STOR2 evaluation-capsule hashing preserve their historical metadata and exact contiguous tensor-byte contract, but no longer materialize another complete `.numpy().tobytes()` object solely to feed SHA-256. The contiguous CPU storage is exposed through Python's buffer protocol and consumed in bounded chunks. Python defines `memoryview` specifically as a non-copying view over buffer-exporting objects.[^perf-p5-memoryview]

TRAIN2 now emits execution-only `train2_persistence.jsonl` telemetry with separate clone, tensor-hash, raw-checkpoint-hash, companion-write, summary-write, and total persistence durations. No continuation field was removed. Model, EMA, optimizer-reference, LR, RNG, exposure, and raw-checkpoint ancestry remain mandatory.

On the bounded 256 MB FP32 state fixture, two fresh-process samples give median TRAIN2 hash time 265.02 ms before versus 142.97 ms after, a **46.05% reduction**. STOR2 capsule-state hashing falls from 248.19 ms to 146.87 ms, a **40.82% reduction**. Additional peak RSS during hashing falls from about 245 MiB to below 1 MiB. Old/new TRAIN2 and STOR2 digests are byte-identical.

### PERF-P5.2 - dataset-format boundary

MACE supports HDF5 and LMDB training-data inputs,[^perf-p5-mace-data] but PERF-P5 does not equate a storage format with an authenticated reusable `AtomicData` graph cache. Existing DATA8 content-addressed fixed-file reuse, DATA6 graph reuse, and EVAL2 graph/prediction caches remain authoritative. A source audit found no remaining DATA8 large-array authority that justified a new persistence schema solely for this gate.

### PERF-P5.3 - optional EVAL2 model-shell/state reload

`MaceCalculatorProvider.load_compatible_model_state(...)` permits one unaccelerated, uncompiled, candidate-only shell to load another deployable model of the exact same class and state structure. It validates model class, state keys, every tensor shape and dtype, and then uses strict `load_state_dict`. PyTorch documents state dictionaries and strict state loading as the standard module-state persistence interface.[^perf-p5-state]

This reuse is **opt-in** and mutable; one shell must never be shared across concurrent inference workers. Source-foundation-bound, CuEq/OEq, or compiled providers reject the path. Full reconstruction remains the default and exact fallback.

The supplied MH-1/`omat_pbe` CPU comparison is exact but negative for performance: fresh calculator construction has 98.86 ms median wall time versus 105.28 ms for state reload, so CPU shell reuse is **not promoted**. Its possible accelerator benefit is deferred to `FINAL-GPU1`, where avoiding repeated accelerator conversion may change the cost balance.

### PERF-P5 acceptance gate

PERF-P5 CPU/control-plane qualification passes because restart/evaluation decisions remain unchanged, interrupted-training continuation remains complete, STOR2 reconstruction remains exact, hashing overhead and transient memory decrease materially, and the optional EVAL2 shell fails closed on incompatible state. No generated performance default changes.

Accelerator-side checkpoint persistence, model-shell reuse, and total TRAIN2/EVAL2 throughput remain final-release evidence under `FINAL-GPU1` and `PERF-CERT1`.

[^perf-p5-memoryview]: Python documentation, *Built-in Types - memoryview*: <https://docs.python.org/3/library/stdtypes.html#memory-views>.
[^perf-p5-state]: PyTorch documentation, *Saving and Loading Models* and `Module.load_state_dict`: <https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html>; <https://docs.pytorch.org/docs/stable/generated/torch.nn.Module.html#torch.nn.Module.load_state_dict>.
[^perf-p5-mace-data]: MACE documentation, *Heterogeneous Data Training* and *Large Dataset Pre-processing*: <https://mace-docs.readthedocs.io/en/latest/guide/heterogeneous_data.html>; <https://mace-docs.readthedocs.io/en/latest/guide/multipreprocessing.html>.

## Gate CUEQ-DEP1 - exact accelerator runtime and dependency freeze

**Implementation status (`0.20.188a0`): control plane complete; positive accelerator evidence deferred to `FINAL-GPU1`.** No GPU qualification is performed during intermediate development.

The e3nn dependency archive does not contain the CuEquivariance runtime required for the workstation acceleration experiment. CUEQ-DEP1 therefore owns a separate content-addressed `CueqDep1RuntimeRecord.v1`. A CPU-only or CuEq-missing machine produces valid **negative evidence**, never an implicit e3nn substitution.

For CUEQ-PHASE1 the frozen execution split is

$$
\text{source inference}=\mathrm{e3nn},
\qquad
\text{training}=\mathrm{CuEq}_{\mathrm{pure}}.
$$

OpenEquivariance is optional at this gate. MACE 0.3.16 training uses pure CuEq for the training realization, so OEQ is recorded only when installed or when a later policy explicitly requires it.

### CUEQ-DEP1 required component authority

The required CuEq stack is three-layered:

1. `cuequivariance`;
2. `cuequivariance_torch`; and
3. `cuequivariance_ops_torch`, provided by a CUDA-major-specific distribution.

NVIDIA documents the core/frontend/ops split and separate CUDA-ops installation.[^cueq-dep1-nvidia] MACE exposes CuEq acceleration through its `enable_cueq` interface.[^cueq-dep1-mace]

The ops import is stable while package discovery accepts, in order, `cuequivariance-ops-torch-cu13`, `...-cu12`, `...-cu11`, and the generic distribution. The exact installed provider is then frozen; the package name alone is never treated as compatibility proof.

Each required Python distribution records version plus SHA-256 identities of installed `METADATA`, `RECORD`, `WHEEL`, optional `direct_url.json`, and the imported module root. Python's `importlib.metadata` is the installed-distribution authority used to retrieve this metadata.[^cueq-dep1-importlib] SHA-256 follows FIPS 180-4.[^cueq-dep1-sha]

For required component $i$, define

$$
C_i = I_i \land H_i^{\mathrm{METADATA}}
     \land H_i^{\mathrm{RECORD}}
     \land H_i^{\mathrm{module}},
$$

where $I_i$ is successful import and each $H$ term denotes a present content identity. Missing installed-package content evidence is a gate failure, not a warning.

### CUEQ-DEP1 device and determinism authority

The runtime record also freezes:

- Python, PyTorch, CUDA runtime, cuDNN, MACE, and e3nn versions;
- GPU model, compute capability, visible memory, driver text, and `nvcc` text when available;
- PyTorch deterministic-algorithm/debug settings;
- cuDNN benchmark/deterministic state;
- CUDA/cuDNN TF32 state and float32 matmul precision; and
- selected CUDA/CuEq environment variables, including allocator and CuEq Triton cache controls when present.

The gate predicate is

$$
Q_{\mathrm{CUEQ\mbox{-}DEP1}}
=R_{\mathrm{MACE/e3nn}} \land V \land C \land A,
$$

where $R_{\mathrm{MACE/e3nn}}$ is the existing MACE source/runtime contract, $V$ is exact MACE/e3nn version agreement, $C$ is content-addressed identity for every required distribution, and $A$ is CUDA plus CuEq core/Torch/ops capability. OEQ joins $C$ and $A$ only when explicitly required.

Two release tools consume this authority:

- `capture_mlff_cueq_dep1_runtime.py` writes the standalone record; and
- `run_mlff_final_gpu_qualification.py` embeds the same record in FINAL-GPU1 preflight v3 (the CUEQ-DEP1 obligation was introduced in v2 and remains preserved in v3).

The final workstation handoff therefore cannot skip the ops layer or substitute a version-only CuEq check.

Architecture revision 55 closed the CUEQ-DEP1 runtime-freeze control plane. The current development host has content-addressed Torch/MACE/e3nn with MACE 0.3.16 and e3nn 0.4.4, but CPU-only PyTorch and no CuEq core/Torch/ops distributions. Its record therefore fails closed with explicit blockers for the three CuEq imports, CUDA availability, and CUDA device inventory. This is implementation evidence only. Final CUEQ-DEP1 qualification requires one release-matched `passed=true` record under `FINAL-GPU1`.

[^cueq-dep1-nvidia]: NVIDIA, *cuEquivariance Documentation - Installation*: <https://docs.nvidia.com/cuda/cuequivariance/>.
[^cueq-dep1-mace]: MACE documentation, *CUDA Acceleration with cuEquivariance Library*: <https://mace-docs.readthedocs.io/en/latest/guide/cuda_acceleration.html>.
[^cueq-dep1-importlib]: Python documentation, *importlib.metadata - Accessing package metadata*: <https://docs.python.org/3/library/importlib.metadata.html>.
[^cueq-dep1-sha]: NIST, *FIPS 180-4: Secure Hash Standard*: <https://doi.org/10.6028/NIST.FIPS.180-4>.

## Gate CUEQ-PHASE1 - training-only selected-head CuEq qualification

**Implementation status (`0.20.189a0`): control plane complete; positive paired accelerator evidence deferred to `FINAL-GPU1`.** No intermediate GPU qualification is performed.

CUEQ-PHASE1 is the first authorized accelerator experiment. It leaves **source-foundation inference, DATA6, pseudolabel generation, source-foundation evaluation, and their cache/generator identities on original MH-1/e3nn**. Only the executable training-foundation realization changes.

The starting artifact is the exact EXTRACT1-qualified derived single-head `omat_pbe` checkpoint whose source SHA/head/extraction evidence already proves its source-head relation under e3nn. Its CuEq realization receives a separate training-realization identity; it does not replace or rename the scientific source-foundation identity.

### CUEQ-PHASE1 paired qualification protocol

Use:

- identical derived starting checkpoint bytes;
- identical DATA8 target and TRUE_DFT replay bundle;
- identical optimizer seed, data order/split identities, precision, objective weights, LR schedule, stopping policy, replay threshold, and epoch/update budget;
- identical lightweight/full validation and evaluation protocols.

Qualification has two levels:

1. **short paired adaptation** of approximately 5-10 epochs, sufficient to reject instability/divergence early; then
2. **at least one representative full authorized training trajectory** before CuEq training becomes production-qualified.

Final weights need not be bit-identical because different CUDA kernels may perturb optimization trajectories. Acceptance is decision/science based. Compare at minimum:

- target validation metrics;
- TRUE_DFT replay validation and hard replay-retention pass/fail;
- loss/gradient/parameter finiteness and stability;
- checkpoint ranking/admissibility;
- selected target-head extraction;
- EVAL2 and available physical verification; and
- wall time, update throughput, peak/reserved VRAM.

A pass authorizes a **phase-separated execution policy** in which source inference remains e3nn and training may use pure CuEq. It does not authorize CuEq DATA6 or pseudolabel generation and does not automatically change generated defaults.

### CUEQ-PHASE1 implementation record - 2026-08-15

`0.20.189a0` adds a dedicated phase-1 evidence authority rather than overloading ACCEL1 static parity or the all-backend campaign configuration. `CueqPhase1TrajectoryRecord.v1` enumerates the paired variables that must be identical: CUEQ-DEP1 runtime, scientific source identity, EXTRACT1 selected-head starting checkpoint, DATA8 bundle, optimizer semantics, split/order identities, objective/LR/stopping/replay policies, validation/EVAL2 protocols, seed, dtype, and epoch/update budget. The only intended independent variable is training realization (`e3nn` versus `cueq_pure`).

`CueqPhase1PairedAssessment.v1` deliberately does **not** require identical final model bytes. It requires both sides to complete the frozen budget, remain finite, pass TRUE_DFT replay retention and checkpoint admissibility, extract the target head, pass EVAL2, and not fail available physical verification. Hard decision disagreement fails closed. Target/replay metric deltas and wall/update/VRAM telemetry are recorded diagnostically; no new tolerance is introduced and no existing threshold is relaxed.

`CueqPhase1QualificationRecord.v1` is the gate-level reducer. It requires at least one passing 5-10 epoch short pair (default 8) and at least one passing representative full pair on the same positive `CueqDep1RuntimeRecord.v1`. A short-only result remains non-authorizing. A positive record sets `phase_separated_training_authorized=true` while permanently keeping `source_cueq_execution_authorized=false` and `generated_default_change_authorized=false` at this gate.

The release tool `tools/qualify_mlff_cueq_phase1.py` builds pair, final qualification, and deferred records without launching accelerator work. FINAL-GPU1 preflight advances to schema v3 and embeds the current phase-1 deferred state. The CPU-only development host therefore proves fail-closed implementation behavior only; the positive short/full training experiment remains deferred to the single final workstation campaign.

## Gate CUEQ-PHASE2 - optional selected-head CuEq source-execution and DATA6 acceleration

CUEQ-PHASE2 is separate and optional. It investigates whether the EXTRACT1-derived single-head `omat_pbe` artifact can serve as an accelerated executable realization of the original six-head MH-1/`omat_pbe` source potential for inference-heavy preparation.

The authority chain is explicit:

```text
scientific foundation
  original six-head MH-1 checkpoint + exact omat_pbe head
        |
        | EXTRACT1 parity/evidence
        v
selected-head executable artifact
  derived single-head omat_pbe checkpoint + source/extraction lineage
        |
        | accelerator realization qualification
        v
derived single-head CuEq executable realization
```

The scientific identity remains the original checkpoint/head. The derived checkpoint and CuEq kernel are execution realization/provenance. Cache reuse, pseudolabel generator identity, DATA6 prediction identity, and evaluation reuse must bind this realization explicitly.

### CUEQ-PHASE2 development corpus

Use a deterministic stratified **development** corpus covering where available:

- compositions/species environments;
- temperatures and strain states;
- high-force/high-difficulty frames;
- unusual local/mobile-ion environments;
- large/high-edge-count graphs; and
- representative ordinary configurations.

Locked-test configurations may validate a frozen decision later but may not tune backend tolerances or realization selection.

### CUEQ-PHASE2 comparisons

Compare original-MH-1/e3nn against derived-single-head/CuEq for:

- total/per-atom energy under the canonical normalization;
- forces;
- stress/virial under the canonical convention;
- invariant descriptors used by DATA6;
- foundation difficulty scores;
- deterministic PCA/FPS inputs and selection fingerprints; and
- pseudolabel/E0 values and generator lineage where requested.

For backend comparison of PCA/FPS behavior, freeze the reference fitted transform when needed so backend perturbation is not conflated with an independently refitted basis. A later full rerun may verify end-to-end selection identity separately.

CUEQ-PHASE2 passes only if the complete original/e3nn -> derived/CuEq observable path satisfies the existing numerical-parity authority, deterministic DATA6/DATA7 selection remains unchanged where required, and pseudolabel/E0 lineage still names the original scientific source together with the qualified execution realization. No tolerance is relaxed solely to recover acceleration.

Direct CuEq execution of the original six-head checkpoint remains unauthorized on the recorded runtime unless a future upstream/runtime change independently requalifies that exact path.

### CUEQ-PHASE2 implementation record - 2026-08-15

`0.20.190a0` implements this optional gate as a separate evidence authority rather than extending the CUEQ-PHASE1 training authorization. `CueqPhase2Policy.v1` locks the original MH-1/`omat_pbe` scientific source, the EXTRACT1 selected-head checkpoint/qualification identity, e3nn as the reference realization, and pure CuEq as the candidate realization. The scientific source digest remains the original six-head potential; the derived checkpoint and runtime are execution provenance only.

`CueqPhase2DevelopmentCorpus.v1` freezes a deterministic stratified development corpus and fails closed if any declared-available stratum is uncovered or if locked-test configurations were used for tuning. `CueqPhase2PathAssessment.v1` reuses the existing `MaceAccelerationParityRecord` for energy/force/stress/descriptor numerical authority, then adds foundation-difficulty parity, frozen-reference-transform PCA/FPS input parity, exact DATA6/DATA7 selection fingerprints, and optional pseudolabel/E0 dual-lineage evidence. No numerical tolerance is added or relaxed.

The candidate execution realization is content-addressed from the CUEQ-DEP1 runtime, frozen source/extraction identities, kernel mode, and dtype. A passing `CueqPhase2QualificationRecord.v1` may authorize only the derived selected-head CuEq source/DATA6/source-evaluation path. Pseudolabel execution additionally requires explicit value/E0 parity and both original scientific-source plus candidate execution-realization lineage. Direct six-head CuEq execution and generated-default changes remain false by construction.

The release tool `tools/qualify_mlff_cueq_phase2.py` validates assessments, assembles qualification records, or emits the deferred fail-closed state without launching GPU work. FINAL-GPU1 preflight advances to v4 and embeds PHASE2 independently of PHASE1. Positive phase-2 accelerator evidence remains deferred to the single final workstation campaign.

## Gate PERF-CERT1 - end-to-end scientific and performance certification

PERF-CERT1 decides whether any accelerated phase should become a recommended or generated policy. Where prior gates provide the corresponding paths, compare:

1. optimized authoritative MH-1/e3nn baseline;
2. e3nn source inference + qualified pure-CuEq training;
3. qualified derived-single-head CuEq source execution + pure-CuEq training; and
4. any intentionally retained fallback profile required for compatibility.

The certification report records:

- per-stage and total preparation wall time;
- TARGET-DATA2B families/s and TARGET-DATA2C selection/scoring time;
- DATA6 frames/s and peak/reserved VRAM/headroom;
- training wall time/update throughput;
- CUDA OOM/backoff frequency;
- target/replay/evaluation metrics and hard-gate decisions;
- descriptor/difficulty/PCA/FPS parity and selection fingerprints;
- selected checkpoint and target-head identities;
- deployment/physical verification outcomes; and
- exact foundation, executable-realization, dependency, and runtime identities.

Performance alone is insufficient. A faster path that changes a hard scientific decision, source-potential semantics, deterministic selection where required, replay retention, or final verification fails certification.

A PERF-CERT1 pass may recommend a new phase-separated acceleration profile and may motivate a later explicit generated-default change. It **must not** rewrite existing campaign TOMLs, reinterpret historical evidence under a new backend/schema, or silently migrate caches. Any generated-default change is a separate documented policy revision with migration/compatibility tests.

### PERF-CERT1 implementation record - 2026-08-15

`0.20.191a0` implements the end-to-end certification and recommendation control plane without executing the deferred GPU campaign. `PerfCert1Policy.v1` freezes the optimized authoritative MH-1/e3nn profile as the baseline, requires a strictly positive end-to-end speedup for an accelerated recommendation, preserves exact hard scientific decisions and deterministic target/DATA6/DATA7 selections, and explicitly forbids direct generated-default mutation.

`PerfCert1ProfileRecord.v1` binds the original scientific source, locked MH-1 and MPA-0 identities, `omat_pbe`, one non-execution scientific-protocol identity, exact workload identity, source/training executable realizations, dependency/runtime identities, selected target size/seed, checkpoint/head identities, EVAL2/deployment/physical decisions, target/replay metrics, and complete preparation/DATA6/TRAIN2/EVAL2 timing, throughput, VRAM, OOM, and backoff telemetry. Different final checkpoint bytes remain admissible when existing scientific authorities and hard decisions agree.

`PerfCert1UpstreamAuthority.v1` keeps CUEQ-PHASE1 and optional CUEQ-PHASE2 independent. Pure-CuEq training requires a positive PHASE1 record; selected-head pure-CuEq source/DATA6/source-evaluation requires a separate positive PHASE2 record on the same CUEQ-DEP1 runtime. A missing or failed PHASE2 profile therefore cannot invalidate a passing e3nn-source + CuEq-training profile.

`PerfCert1ProfileAssessment.v1` compares each profile to the authoritative baseline. A faster candidate fails if source semantics, scientific protocol/workload, target/DATA6/DATA7 selection, replay retention, checkpoint admissibility, EVAL2, available deployment/physical verification, or other frozen hard decisions change. Locked-test tuning is a hard failure. `PerfCert1QualificationRecord.v1` recommends the passing accelerated profile with the lowest total wall time (profile ID is the deterministic tie-break), while `generated_default_change_authorized` remains false and a later explicit policy revision is required before any generated-default migration.

The release tool `tools/qualify_mlff_perf_cert1.py` assembles, validates, or emits a deferred fail-closed PERF-CERT1 record without launching accelerator work. FINAL-GPU1 preflight advances to v5 and embeds the independent PERF-CERT1 state. Positive e3nn/CuEq profile timing and scientific evidence remain deferred to the single final workstation campaign.

## Explicit non-goals and preserved optimizations

This roadmap deliberately does **not** authorize:

- approximate nearest-neighbor search for authoritative TARGET-DATA2B coverage;
- approximate/randomized FPS replacing exact deterministic authoritative selection;
- GPU FPS if altered reduction/tie behavior changes the frozen order;
- reference-frame subsampling merely for performance;
- reducing the fixed reference-mass fraction beta;
- sparse/cutoff structural features replacing the current dense feature definition without a separate scientific revision;
- relaxing e3nn/CuEq numerical parity thresholds merely to recover accelerator use;
- direct original-six-head MH-1/CuEq source inference after the recorded parity failure unless independently requalified;
- stock MACE HDF5/LMDB conversion represented as a precomputed graph cache;
- using locked-test evidence to tune accelerator or performance-policy choices; or
- weakening checkpoint/restart evidence merely to save I/O.

The audit also confirms that several earlier optimizations are already present and should be preserved rather than reimplemented:

- raw pair geometry is shared across rules with the same center/neighbor species-pair group;
- DATA6 structural tables already use native sharded persistence;
- DATA7 already includes several bulk/columnar and dimensional-reduction optimizations from prior performance work;
- EVAL2 already has persistent graph/prediction caching, byte-bounded graph reuse, frozen replay prediction reuse, and staged CPU/GPU execution; and
- existing recovery journals/content-addressed artifacts remain the durability boundaries during execution pipelining.

## Final optimization-completion rule

The post-major-revision optimization program is complete only when:

1. PERF-BASE0 has frozen a usable numerical/performance oracle;
2. TARGET-DATA2B no longer expands its large scientific matrices through Python-object/JSON authority and its exact fixed-mass coverage scales under P0;
3. TARGET-DATA2C/DATA7 share the qualified exact selector/coverage engine and no longer require `O(K^2)` persistent selected-distance memory;
4. SIZE-HALVE1 full-ladder hard-coverage plus successive-fidelity semantics remain the only current generated target-size authority; historical PERF-P2 lazy truncation cannot re-enter through an optimization path;
5. PERF-P2R is implementation-qualified across the complete SIZE-FIDELITY1 parameter grid, including exact full-ladder/corpus/preprocessing reuse, target-only coarse evaluation, exact pause/resume continuation, and stage-aware scheduling, without claiming GPU speedup before FINAL-GPU1;
6. SIZE-FIDELITY1 and PERF-P2R accelerator acceptance are both closed in FINAL-GPU1: exact monitor/full promotion equivalence, 100% retention of both eventual 30-epoch target finalists through coarse and epoch-10 screens across frozen seeds, and measured whole-funnel benefit on the authorizing MACE/GPU runtime;
7. CPU structural/reduction work respects bounded stage resource scopes and avoids major per-frame wrapper/allocation overhead;
8. DATA6 uses workload-correct capacity evidence and bounded overlapped graph/inference/persistence execution;
9. one complete optimized MH-1/`omat_pbe`/e3nn campaign is frozen as the authoritative baseline;
10. late TRAIN2/EVAL2 hardening preserves restart/evaluation authority;
11. any CuEq path is independently dependency-frozen and phase-qualified in FINAL-GPU1; and
12. PERF-CERT1 demonstrates that the recommended production profile preserves all hard scientific decisions while providing a measured operational benefit.

The optimization authority is intentionally asymmetric: **exact CPU/storage scaling is fixed first; DATA6 memory safety and pipeline throughput follow; e3nn remains the scientific source-foundation baseline; CuEq training is qualified independently; CuEq source execution remains optional and separately gated; and only final end-to-end certification may motivate a future generated-policy change.**


## Gate FINAL-GPU1 - release-handoff implementation (revision 59)

**Implementation status (`0.20.192a0`): release-handoff authority complete; positive CUDA/CuEq execution pending on the final workstation package.**

Revision 59 closes the last CPU/control-plane gap before workstation execution. FINAL-GPU1 is no longer only a readiness preflight. `mdstats.training_data.final_gpu1` defines an immutable evidence matrix, content-addressed evidence registrations, and a fail-closed final reducer. `tools/run_mlff_final_gpu_qualification.py` advances to preflight v6 and provides resumable `preflight`, `init`, `record`, `status`, `verify`, and `reduce` operations.

The final matrix distinguishes three acceptance classes so legacy direct-six-head CuEq results cannot incorrectly veto the qualified phase-separated design:

1. **must-pass release blockers** - CUEQ-DEP1, the complete authoritative MH-1/`omat_pbe`/e3nn baseline, SIZE-FIDELITY1, PERF-P2R, VRAM1/PERF-P4 memory-safety/throughput authority, CUEQ-PHASE1, and PERF-CERT1;
2. **measure-only optimization evidence** - PREC3, the historical MH1-ACCEL1/MH1-DATA6-1/MH1-TRAIN1/MH1-CERT1 direct-CuEq probes, and PERF-P5 accelerator persistence/reload. These experiments must be recorded, but a negative result is admissible when the optimization stays disabled or is superseded by the phase-separated authority; and
3. **optional capability evidence** - CUEQ-PHASE2 selected-head source/DATA6 acceleration and MH1-DEPLOY1 ML-IAP/LAMMPS deployment capability.

Every registered artifact is SHA-256 addressed and bound to the exact release archive. All CuEq-dependent matrix items are explicitly runtime-bound to the same `CueqDep1RuntimeRecord.v1` digest; a missing runtime binding is itself a fail-closed condition rather than an implicit match. Evidence registrations are immutable within a run root, and initialization refuses foundation files that do not match the locked MH-1/MPA-0 identities. Before status/reduction, the handoff re-hashes the release archive, both foundation models, every evidence-registration record, and every copied evidence artifact. It also requires the serialized policy to equal the canonical FINAL-GPU1 policy and the manifest matrix to retain the exact ordered gate set, acceptance classes, record paths, and valid state domain. The verifier rejects post-registration mutation, path escape, stale or structurally altered matrix state, cross-release evidence, cross-runtime evidence, missing required measurements, failed must-pass gates, locked foundation-model drift, a negative runtime freeze, or a negative/missing PERF-CERT1 authority. The structured CUEQ-DEP1, PHASE1, PHASE2, and PERF-CERT1 content digests are cross-checked rather than trusting file names or user-supplied status strings.

`generated_default_change_authorized` remains false in the FINAL-GPU1 authority itself. A successful final run may carry a PERF-CERT1 recommendation and set `generated_default_policy_revision_required=true`; migration of generated campaign defaults remains a separate explicit versioned policy revision.

The handoff package includes the source release plus the supplied locked foundation models, LTA training corpus, TRUE_DFT replay corpus, and offline reference dependency sources. No positive accelerator evidence is manufactured on the CPU development host.


## Gate CUEQ-DEFAULT1 - generated TRAIN2 CuEq default policy (revision 60)

**Implementation status (`0.20.193a0`): generated-policy migration implemented; source/DATA6/evaluation remain e3nn.**

Revision 60 is the explicit policy revision anticipated by CUEQ-PHASE1, PERF-CERT1, and FINAL-GPU1. A newly generated campaign now freezes `backend = "e3nn"` for source-foundation inference, DATA6, pseudolabel generation, checkpoint evaluation, and verification, and freezes `training_backend = "cueq"` for TRAIN2. `only_cueq=false` remains mandatory so saved fine-tuned checkpoints are converted back to portable e3nn form.

The migration is prospective and compatibility-preserving. Historical TOML without `training_backend` keeps the original unified backend semantics, so existing campaigns, caches, and protocol identities are not reinterpreted. `--training-backend e3nn` remains an explicit reference-run override.

`TrainingAccelerationRealizationRecord.v1` is a dedicated TRAIN2-only authority that binds the exact selected-head training checkpoint, requested backend, pure training kernel, device/dtype, runtime versions, and training parity digest. It intentionally carries no source-foundation inference authority. `doctor` therefore freezes two independent realizations for new phase-separated campaigns: the source realization used by DATA6/evaluation and the training realization used by DATA8/TRAIN2. Missing CuEq runtime capability or failed pure-training parity fails closed when `require_available=true`; no e3nn fallback is performed implicitly.

DATA8 optimizer protocol identity consumes the training policy/realization digest. The bounded preflight verifies the generated CuEq training flags and requires CuEq activation evidence in the MACE training log, then evaluates the exported portable checkpoint through the source policy. All evaluation/verification policies continue to use the source/e3nn acceleration identity.

This explicit policy change does not rewrite or reinterpret the immutable `generated_default_change_authorized=false` fields in CUEQ-PHASE1, PERF-CERT1, or FINAL-GPU1. Those fields correctly stated that those gates themselves could not mutate defaults. Revision 60 is the separate policy migration requested after those gates. Positive CUDA performance certification remains independent of this generated-default choice.


## Gate CUEQ-DEFAULT1-HF1 - workstation parity/reporting hotfix (revision 61)

**Implementation status (`0.20.194a0`): implemented.**

The first workstation execution of the revision-60 generated default exposed two independent defects. The v2 foundation configuration contract had already replaced the former aggregate `backend` field with `source_backend` and `training_backend`, but the doctor display still indexed the retired key. That display path now reports both phase authorities and remains identity-neutral.

The selected-head TRAIN2 preflight also reused the generic ACCEL1 FP32 source/DATA6 tolerance (`rtol=1e-5`, `atol=1e-6`). That is stricter than the selected-head roundoff envelope already recorded before CUEQ-DEFAULT1: the earlier workstation experiment measured approximately `Emax=1.272e-6`, `Fmax=1.669e-6`, `Smax=3.772e-8`, and `Dmax=1.192e-6` with an identical deterministic selection fingerprint. Revision 61 therefore freezes a **TRAIN2-only** FP32 policy of `rtol=1e-5`, `atol=2e-6`; FP64 remains `rtol=1e-10`, `atol=1e-12`. This revision-61 floor is historical after CUEQ-DEFAULT1-HF2; revision 82 supersedes the active TRAIN2 FP32 absolute ceiling with `1e-5` while leaving the source/DATA6 and FP64 authorities unchanged.

This is deliberately not a global ACCEL1 relaxation. Source-foundation inference, DATA6, pseudolabel generation, source evaluation, and any PHASE2 source-execution comparison retain the original `1e-5/1e-6` FP32 authority. The training parity policy is serialized separately beside `TrainingAccelerationRealizationRecord.v1` and its parity record. Selection identity remains mandatory, and missing runtime capability, non-finite values, or deltas outside the TRAIN2 policy fail closed without an implicit e3nn fallback.

## Gate DATA6-RECOVERY-HF1 - verified recovery NumPy import repair (revision 62)

**Implementation status (`0.20.195a0`): implemented.**

Revision 62 restores `import numpy as np` for verified DATA6 recovery `np.linspace` sampling. Failure was pre-inference; scientific/restart identities stay unchanged. A regression now forces the branch.



## Gate FOUNDATION-AUDIT1-HF1 - explicit audit configuration plumbing (revision 63)

**Implementation status (`0.20.196a0`): implemented.**

Revision 63 makes the campaign configuration an explicit keyword-only dependency of `_ensure_foundation_target_audit()`. This repairs the workstation `NameError: name 'cfg' is not defined` raised while reading the FOUNDATION-AUDIT1 temporary-memory setting after DATA6 had completed. `_prepare_materialization()` now passes the active configuration, and regression coverage verifies exact MiB-to-byte propagation with a non-default value.

The repair is orchestration-only. FOUNDATION-AUDIT1 metric definitions, target-data role authority, foundation identities, DATA6 descriptors/predictions, e3nn source execution, CuEq TRAIN2 execution, deterministic selection, and restart/content digests are unchanged. Existing valid DATA6 state remains reusable after upgrading.

## Gate TARGET-DATA2C-RESCUE1 - bounded upper-ladder coverage rescue (revision 64)

**Implementation status (`0.20.197a0`): implemented.**

Revision 64 corrects the fixed target-size ceiling exposed by the first full production LTA run with complete DATA6-derived TARGET-DATA2B coverage families. Earlier PERF-P2 evidence had qualified the 128--8192 ladder before those model-derived families were available, so the historical observation that `n2048`, `n4096`, and `n8192` passed could not justify treating 8192 as a universal production coverage ceiling.

TARGET-DATA2C therefore advances to `mdstats.target-data2c.ladder.2026-08.v4`. The original power-of-two sequence remains the **base ladder** and is evaluated first. When it supplies fewer than TARGET-DATA2D `min_coverage_qualifiers` (default 3), the authority activates a deterministic **bounded upper-ladder rescue**. Let `P` be the smallest TARGET-DATA2A development pool across label domains and let `A` be the smallest base rung. Rescue candidates are `floor((k P / 8) / A) A` for `k = 3, 4, 5, 6, 7`, retaining unique candidates strictly above the largest base rung and below `P`. Thus the largest legal rescue prefix is at most 7/8 of the common development pool and at least 1/8 remains outside training for leakage-safe EVAL2.

The rescue is a candidate-density correction, **not a coverage relaxation**. TARGET-DATA2B's default 0.95 reference-mass threshold, extent checks, required strata, mandatory quota/interval reservations, exact quota-first/FPS ordering, and nested monotonicity contracts remain unchanged. Once activated, every globally materializable rescue candidate is retained for the Stage-B0 epoch-3 learning screen; hard coverage still acts only as an admissibility gate and cannot rank/truncate the learning candidates.

`TargetDataLadderPlan.v4` content-addresses whether rescue was activated, the deterministic rescue candidate sequence, and the minimum qualifier requirement that caused the decision. Changing `min_coverage_qualifiers` invalidates the stored ladder on restart. All pre-v4 ladders are stale for generated campaigns and rebuild from the frozen TARGET-DATA2A/TARGET-DATA2B authorities without requiring DATA6 to be recomputed when those upstream records remain valid.

If the rescue remains insufficient, TARGET-DATA2D now fails with evidence-rich diagnostics: rescue state/candidates and, at the largest materialized rung, each failed required family's covered reference mass versus threshold, extent failures, required-stratum deficits, and unsatisfied mandatory obligations. This turns a generic all-rungs-failed message into a concrete basis for the next scientific decision.

Acceleration policy is orthogonal to this correction: source inference, DATA6, pseudolabel/evaluation, and verification remain e3nn, while TRAIN2 remains the CUEQ-DEFAULT1 pure-CuEq training realization.


## Gate TARGET-DATA2-MVPLAN1 - multi-view coverage-optimized target-data roadmap freeze (revision 65)

**Implementation status (`0.20.198a0`): architecture/roadmap only; executable TARGET-DATA2C remains revision-64 v4 until the migration gate is qualified.**

Revision 65 freezes the replacement roadmap for the inefficient random/semi-random target-data selection exposed by the production LTA coverage failure. The objective is not to flatten or "smooth" the empirical feature distribution. The objective is to construct the smallest deterministic nested target-data subsets that maximize physically relevant multi-view coverage while preserving dense-basin representation, mandatory rare states, provenance/correlation constraints, and an independent hard coverage audit.

The fixed generated target-size ceiling becomes **16,384 configurations** for the planned authority. Together with the existing power-of-two lower rungs, the planned candidate ladder contains exactly eight sizes:

```text
128, 256, 512, 1024, 2048, 4096, 8192, 16384
```

The 16,384 ceiling is a hard candidate-size cap, not permission to approach the complete reference/development pool by brute force. The current revision-64 dynamic 3/8--7/8 rescue remains active only until the new selector is scientifically qualified and migrated; after migration it is historical compatibility evidence and no generated campaign may silently exceed 16,384.

### Frozen scientific principles

1. **Feasibility precedes subset optimization.** Before optimizing any subset, compute the maximum TARGET-DATA2B hard coverage attainable from the complete eligible development pool. If the full pool cannot satisfy a required feature family, extent, or protected stratum at the frozen threshold, the terminal status is `support_mismatch`. Increasing target size or changing subset selection cannot repair missing support.
2. **Hard coverage remains independent and unchanged.** The default `coverage_threshold = 0.95`, required extents, required strata, mandatory reservations, DATA5 leakage/correlation boundaries, and blinded/locked-test rules are not relaxed by the selector.
3. **Coverage optimization is robust across feature views.** The primary selector objective minimizes the worst normalized coverage deficit across required feature families. Aggregate covered reference mass, unique contribution, and geometric diversity are secondary/tie-break objectives; no weighted average may hide one badly under-covered feature family.
4. **Redundancy means negligible unique coverage, not merely high local density.** A selected structure may be removed only when leave-one-out removal loses negligible unique coverage and violates no mandatory stratum/provenance constraint. A multi-view clustering score may diagnose redundancy or break ties but is not deletion authority.
5. **Replacement is deficit-directed.** Replacement candidates are chosen for maximum gain against currently uncovered/under-covered witnesses, not regenerated randomly. Random or new-DFT acquisition is considered only when no eligible development structure can cover a required witness.
6. **Nestedness is exact.** The planned eight sizes are prefixes of one deterministic progressive selection order. Earlier size boundaries are frozen before later shells are repaired, so `S_128 subset S_256 subset ... subset S_16384` holds exactly and target-size learning differences are not confounded by resampling.
7. **Dense physical basins are not artificially flattened.** The selector rewards incremental reference-mass coverage with diminishing returns for near-duplicates; it does not maximize pairwise distance alone. Rare valid states are protected explicitly, while existing data-quality/provenance checks veto invalid/suspect outliers before diversity can reward them.
8. **Correlation structure is authoritative.** Source/trajectory balancing and temporal-correlation constraints are derived from existing DATA5 correlation/source units rather than ad hoc frame-spacing heuristics.
9. **Selector and verifier remain separate.** Selection may use deterministic development-side coverage witnesses/indexes, but TARGET-DATA2D remains the independent hard coverage authority. Locked-test data cannot tune selector weights, radii, repair budgets, or tie rules.
10. **The 3/10/30 funnel remains a learning-sufficiency authority.** The eight fixed size candidates are the Stage-B0 population. All eight may receive the bounded 3-epoch coarse training evidence, but a hard-coverage-failing size is ineligible to survive. At least four hard-coverage-qualified candidates are therefore required before the 10-epoch stage. The successive-fidelity survivor counts are exactly `8 -> 4 -> 2 -> 1` at `3 -> 10 -> 30` epochs; the arrows refer to candidate count, not dataset-size halving.

The new funnel therefore raises the planned minimum hard-coverage qualifier requirement from three to **four**: four admissible candidates are required to populate the 10-epoch stage without allowing a coverage-failing size to advance. If the complete development pool is feasible but fewer than four of the eight optimized fixed rungs qualify, the authority reports an explicit bounded-capacity/qualifier insufficiency rather than silently adding target sizes above 16,384.

### Planned implementation gates

#### Gate TARGET-DATA2B-FEAS1 - full-pool feasibility and support witness authority

**Purpose:** establish whether the frozen 95% multi-view coverage target is achievable before any subset-size decision.

**Implementation:** evaluate every required TARGET-DATA2B family, extent, protected stratum, and mandatory support condition against the complete eligible development pool; record per-family maximum covered mass and nearest eligible candidate distance for every uncovered witness; serialize a content-addressed `feasible | support_mismatch` result without changing target selection.

**Acceptance:** exact deterministic replay; no locked-test access; diagnostics identify the limiting feature families/witnesses; existing TARGET-DATA2A/B and DATA6 identities are reused rather than recomputed when valid.

#### Gate TARGET-DATA2C-MVIDX1 - exact multi-view coverage-index substrate

**Purpose:** make repeated marginal-coverage queries tractable without constructing dense all-pairs matrices.

**Implementation:** freeze per-view witness identities, authoritative radii/scales, candidate-to-witness coverage maps, weighted reference mass, and selector/audit witness roles. Use chunked sparse/bitset-style representations where exact; provide scalar/reference fallbacks for verification.

**Acceptance:** indexed coverage and marginal-gain queries are decision-equivalent to the authoritative TARGET-DATA2B calculations on deterministic fixtures and sampled production blocks; serialization/restart digests are stable; memory use is bounded and independent of an `N x N` dense matrix.

#### Gate TARGET-DATA2C-MVSEL1 - robust deterministic progressive selector

**Purpose:** replace random/semi-random ordering with direct first-principles coverage optimization.

**Implementation:** seed mandatory reservations first, then greedily extend one global order to 16,384 using lexicographic priorities: worst-view normalized deficit, mandatory/protected-stratum deficit, newly covered weighted reference mass, representative/facility gain, then normalized diversity. Exact frame identity provides the final deterministic tie-break.

**Acceptance:** exact nested prefixes at all eight planned sizes; monotonic coverage; deterministic replay across process counts; no stochastic seed dependence; mandatory and DATA5 correlation constraints cannot be traded for aggregate coverage.

#### Gate TARGET-DATA2C-REPAIR1 - unique-contribution pruning and deficit-directed shell exchange

**Purpose:** remove residual redundancy that greedy construction leaves behind without destabilizing previously frozen smaller rungs.

**Implementation:** compute leave-one-out unique coverage for the active shell; identify only negligible-contribution, non-mandatory candidates as removable; replace them with unselected candidates that maximize the current worst-view/uncovered-witness gain. Exchanges operate only inside the newly added shell, require strict lexicographic improvement, and stop at a frozen bounded attempt/swap budget.

**Acceptance:** no exchange reduces a frozen lower-rung prefix, hard coverage component, protected stratum, or provenance constraint; no oscillation; interrupted/restarted repair reproduces the same terminal subset and evidence digest; clustering score remains diagnostic only.

#### Gate TARGET-DATA2C-MVPERF1 - exact-equivalence selector performance hardening

**Purpose:** make the new selector practical on the complete ~tens-of-thousands-frame production corpus without changing decisions.

**Implementation:** benchmark and optimize bitset/sparse coverage updates, lazy-greedy upper bounds, candidate chunking, vectorization, CPU parallelism, and bounded memory. Approximate nearest-neighbor or approximate coverage methods are forbidden unless a later scientific gate separately qualifies them.

**Acceptance:** byte/decision-equivalent selected frame identities and coverage reports versus the unoptimized MVSEL1/REPAIR1 reference; measured wall-time/RSS evidence on representative and full-corpus fixtures; no locked-test or GPU-specific tuning authority.

#### Gate TARGET-DATA2C-MVQUAL1 - same-N scientific qualification and capacity diagnosis

**Purpose:** establish that the new selector improves coverage efficiency rather than merely producing a different subset.

**Implementation:** A/B the legacy current selector and the frozen MV selector at identical cardinalities `128..16384` on deterministic development qualification corpora. Record minimum-view coverage, per-view/reference-mass coverage, protected-stratum coverage, redundancy fraction, uncovered witness count/mass, source/correlation diversity, and smallest 95%-qualified rung. Re-run the independent TARGET-DATA2D audit rather than accepting selector-internal scores.

**Acceptance:** mandatory predicates never regress; the new selector does not increase the smallest independently coverage-qualified target size on qualification corpora; the known LTA under-coverage case must either obtain a qualified bounded rung or terminate with an evidence-backed `capacity_limited`/`support_mismatch` diagnosis. Locked-test data may validate a frozen algorithm later but may not tune it.

#### Gate SIZE-HALVE2 - fixed eight-rung 3/10/30 funnel integration

**Purpose:** integrate the 16,384 ceiling and optimized nested ladder with the existing successive-fidelity training authority.

**Implementation:** freeze exactly eight generated candidate sizes `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`. Stage B0 obtains 3-epoch coarse evidence for the eight candidates; only hard-coverage-qualified candidates are survivor-eligible and at least four qualifiers are required. The frozen ranking/equivalence rules reduce `8 -> 4`; Stage B1 reduces `4 -> 2` at 10 epochs; Stage C reduces `2 -> 1` at 30 epochs using the full existing EVAL2/physical qualification chain. The 16,384 ceiling cannot be exceeded by rescue.

**Acceptance:** no coverage-failing candidate can survive B0; fewer than four hard qualifiers fails closed before B1; continuation ancestry preserves optimizer/RNG state across 3/10/30 endpoints; existing largest-boundary tie protection and final smaller-size practical-equivalence preference remain explicit.

#### Gate SIZE-FIDELITY2 - survivor-fidelity requalification for MV selection and 16k ceiling

**Purpose:** re-establish that the 3- and 10-epoch screens retain the candidates that matter at 30 epochs after changing both subset geometry and the candidate ladder.

**Implementation:** repeat the exhaustive SIZE-FIDELITY1-style calibration on the frozen MV-selected eight-rung ladder for the required optimizer seeds, with halving disabled during calibration. Retrospectively evaluate the frozen 3- and 10-epoch survivor policies against the uninterrupted 30-epoch trajectories.

**Acceptance:** the existing survivor-recall/non-regression authority must pass for the new selector/16k population before generated campaigns may rely on `8 -> 4 -> 2 -> 1`. GPU-dependent MACE qualification remains a workstation/final qualification activity and is not inferred from CPU control-plane tests.

#### Gate TARGET-DATA2C-MVMIGRATE1 - generated-policy migration and RESCUE1 retirement

**Purpose:** switch generated campaigns only after the complete selector, audit, performance, and funnel authorities are qualified.

**Implementation:** advance TARGET-DATA2C/TARGET-DATA2D/TARGET-DATA2E record versions, make the MV selector and fixed 16,384 ceiling the generated default, raise the generated minimum hard qualifiers to four, and retire revision-64 dynamic upper-ladder rescue from generated semantics. Historical v4 rescue records remain readable/auditable; incompatible stored selector/ladder records rebuild from frozen upstream TARGET-DATA2A/B/DATA6 state without recomputing valid expensive upstream evidence.

**Acceptance:** new campaigns use only the MV/fixed-ceiling authority; old records cannot masquerade as new authority; restart invalidation is minimal and content-addressed; e3nn source/DATA6 and CuEq TRAIN2 policy remain orthogonal and unchanged.

### Frozen dependency order

```text
TARGET-DATA2C-RESCUE1 (current executable fallback)
        |
        v
TARGET-DATA2B-FEAS1
        |
        v
TARGET-DATA2C-MVIDX1
        |
        v
TARGET-DATA2C-MVSEL1
        |
        v
TARGET-DATA2C-REPAIR1
        |
        v
TARGET-DATA2C-MVPERF1
        |
        v
TARGET-DATA2C-MVQUAL1
        |
        v
SIZE-HALVE2
        |
        v
SIZE-FIDELITY2
        |
        v
TARGET-DATA2C-MVMIGRATE1
        |
        v
new generated TARGET-DATA2C/D/E authority
```

No later gate may weaken FEAS1/support diagnostics, the independent 0.95 hard coverage authority, exact nestedness, protected strata, DATA5 leakage/correlation boundaries, or the prohibition on locked-test tuning. Performance work may change execution only; scientific selector changes require a new explicit architecture revision.

## Gate TARGET-DATA2-MVPLAN2 - optimized multi-view selector implementation freeze (revision 66)

**Implementation status (`0.20.199a0`): architecture/roadmap hardening only; executable TARGET-DATA2C remains revision-64 v4 until `TARGET-DATA2C-MVMIGRATE1` is qualified.**

Revision 66 supersedes the *planned semantics* of TARGET-DATA2-MVPLAN1 while preserving revision 65 as historical architecture evidence. The nine implementation-gate names and their dependency order remain unchanged. This revision freezes the algorithmic and performance details required before Gate TARGET-DATA2B-FEAS1 begins.

The target-size population remains exactly:

```text
128, 256, 512, 1024, 2048, 4096, 8192, 16384
```

`16384` is the generated hard ceiling. The independent TARGET-DATA2B/TARGET-DATA2D default hard-coverage threshold remains `0.95`. Revision-64 dynamic upper rescue remains executable only as the current compatibility path and is retired only by MVMIGRATE1.

### Revision-66 corrections to the frozen scientific model

1. **Full-pool self-coverage is not a support-feasibility authority.** In the current TARGET-DATA2B/C domain, selectable development frames are also coverage witnesses; selecting the entire pool therefore covers each witness by itself. FEAS1 must treat full-pool self-coverage as a graph/index consistency check, not as evidence that a compact subset can represent the domain.
2. **Meaningful FEAS1 evidence is cross-support plus a cardinality lower bound.** For each witness, FEAS1 measures support after excluding the witness itself and, where the frozen DATA5 correlation/source unit permits, its own correlation unit. It records fragile-support degree distributions and an optimistic lower bound on the number of candidates required to cover each hard feature family/obligation. If even the optimistic bound exceeds 16,384, the planned authority may report `provably_capacity_infeasible` before running MVSEL1.
3. **Hard extents, protected strata, and mandatory reservations are first-class selector obligations.** They are not inferred indirectly from aggregate coverage. Each required lower/upper extent and protected stratum is indexed to the eligible candidates that can satisfy it. A candidate satisfying several currently unsatisfied hard obligations may dominate an otherwise larger aggregate coverage gain.
4. **Coverage optimization remains view-robust.** No weighted average may hide one badly deficient required feature family. Hard obligations and the worst normalized required-view deficit dominate the selection order; total newly covered mass, provenance balance, density-aware representation, and geometric diversity are subordinate criteria.
5. **Redundancy is exact marginal scientific contribution.** A frame is removable only if its removal causes negligible unique coverage loss and no hard-obligation/provenance loss. Neighbor count or multi-view clustering score remains diagnostic/tie-break evidence only.
6. **Nestedness remains exact and constructive.** Every planned rung is a prefix of one deterministic ordered master sequence. Repair may change only the active shell. A replacement inherits the removed frame's master-sequence rank; lower frozen ranks are never reordered.
7. **Selection and verification remain separate.** The selector may use frozen development-side witness/index structures, but the independent TARGET-DATA2D authority certifies every frozen rung. Locked-test evidence cannot tune radii, score weights, swap budgets, tie tolerances, or performance heuristics.
8. **No active acquisition is introduced here.** Failure of a fixed eligible corpus is reported diagnostically. Generating new AIMD/DFT configurations belongs to a later active-learning/data-acquisition authority, not TARGET-DATA2 subset selection.

### Determinism and numerical authority

Scientific selection must be reproducible from frozen inputs regardless of process count, chunk order, Python hash iteration order, or native-thread scheduling. Candidate arbitration therefore uses a normative deterministic key whose semantic priorities are:

```text
hard-obligation gain
worst-view normalized coverage gain
new weighted reference-mass gain
provenance/correlation balance
representative-density gain
normalized diversity
stable frame UID
```

Coverage and candidate-gain accumulation are FP64 scientific quantities even when upstream descriptors were produced in an approved FP32 realization. Integer counts remain integer. Parallel reductions use deterministic chunk ordering, and score comparisons define an explicit frozen equivalence tolerance before stable frame UID resolves the final tie. No FP32-only gain/ranking authority is permitted.

### Authoritative evidence versus reconstructible execution caches

Revision 66 separates scientific evidence from execution state.

**Authoritative/content-addressed evidence includes:** frozen descriptor/transform identities; witness identities and weights; metric/radius identities; exact candidate-witness adjacency; hard extent/stratum/mandatory obligation indices; ordered selected frame UIDs and prefix digests; independent coverage reports; provenance/correlation identities; and final repair decisions.

**Reconstructible execution caches include:** covered flags; witness multiplicity arrays; current marginal-gain arrays; heaps/priority queues; worker shards; scratch buffers; lazy-rescore upper bounds; and temporary candidate shortlists. These caches may be discarded and rebuilt from authoritative evidence without changing scientific identity.

Large graph/selection arrays must use content-addressed binary sidecars rather than giant JSON integer lists. Array metadata records shape, dtype, byte order, policy/identity digest, and SHA-256; hashing follows the streamed/memoryview persistence pattern established by PERF-P5.

### Optimized implementation gates

#### Gate TARGET-DATA2B-FEAS1 - self-consistency, cross-support fragility, and capacity lower bounds

**Purpose:** determine whether the frozen coverage graph is internally valid, where the candidate universe is fragile, and whether the 16,384 ceiling is provably insufficient before expensive subset optimization.

**Implementation requirements:**
- verify that the full eligible candidate pool self-covers every hard witness/obligation expected to be self-coverable; failure is an indexing/domain defect;
- compute cross-support after excluding the witness itself and, where authorized, its own DATA5 correlation/source unit;
- record weighted witness mass by candidate degree (`1`, `<=2`, `<=4`, `<=8`, and configured higher diagnostic bins) per feature family and protected stratum;
- derive optimistic singleton coverage gains and mandatory-obligation lower bounds, combine them into a conservative `K_min_lower_bound`, and compare it with the fixed 16,384 ceiling;
- do not build target subsets or change TARGET-DATA2C runtime behavior.

**Planned states:** `self_consistent`, `cross_support_fragile`, `optimization_required`, and `provably_capacity_infeasible`. Cross-support fragility is diagnostic unless an independently frozen hard support predicate says otherwise.

**Acceptance:** exact deterministic replay; no locked-test access; no full `N x N` matrix; diagnostics identify limiting feature families/obligations; valid TARGET-DATA2A/B/DATA6 identities are reused.

#### Gate TARGET-DATA2C-MVIDX1 - exact sparse bidirectional coverage graph and hard-obligation index

**Purpose:** make exact marginal coverage and repair operations sparse, incremental, restartable, and memory bounded.

**Normative substrate:** for each required feature family, construct both candidate-to-witness and witness-to-candidate sparse adjacency using CSR/CSC-equivalent contiguous arrays. Use compact integer indices (`uint32` when cardinalities permit), 64-bit offsets where required by edge count, and FP64 scientific weights. Dense persistent all-pairs distance matrices and Python-object neighbor sets/dicts are forbidden in the production hot path.

Hard extent obligations are separately indexed as explicit lower/upper candidate sets; protected strata, mandatory reservations, and DATA5 source/correlation units are first-class indexed constraints. Family shards may be memory mapped and processed one family at a time.

**Acceptance:** indexed coverage and exact marginal queries are decision-equivalent to authoritative TARGET-DATA2B calculations on deterministic fixtures and sampled production blocks; forward and inverse adjacency agree exactly; graph serialization/restart digests are stable; scientific graph evidence is independent from reconstructible selector caches.

#### Gate TARGET-DATA2C-MVSEL1 - two-phase deterministic progressive selector

**Purpose:** construct one ordered nested coreset whose prefixes maximize hard multi-view coverage efficiently without flattening the physical distribution.

**Phase A - hard coverage construction:** mandatory reservations and currently unsatisfied hard extents/strata are serviced first. Among otherwise admissible candidates, the selector prioritizes the worst normalized required-view deficit, then newly covered weighted reference mass, provenance/correlation balance, density-aware representative gain, normalized diversity, and stable frame UID. Coverage edges are processed incrementally rather than recomputed globally.

**Phase B - representative filling:** after all hard views/obligations that can pass have reached their target at the current prefix, additional cardinality is filled using a frozen density-aware representative/facility objective with diminishing returns. Dense physical basins may receive multiple representatives proportional to reference importance, but near-duplicates have progressively smaller utility. Pure maximin/FPS cannot become the primary post-coverage authority and invalid/suspect outliers remain vetoed by existing quality/provenance checks.

**Incremental state:** maintain per-witness covered/multiplicity state, per-view current coverage, and per-candidate marginal gain. When a witness becomes newly covered, use inverse adjacency to update only candidates affected by that witness. Full candidate x witness rescoring after every selection is forbidden.

**Rung invariants:** exact requested cardinality; unique eligible UIDs; no forbidden-role frames; mandatory/protected obligations preserved; `S_N subset S_2N`; binary hard coverage non-decreasing with nested cardinality; ordered-prefix digest reproduces membership exactly. Record marginal/shell gain for saturation diagnosis, but saturation may not override the fixed rung or 0.95 authority.

#### Gate TARGET-DATA2C-REPAIR1 - multiplicity-based unique contribution and deficit-directed shell exchange

**Purpose:** remove residual shell redundancy left by greedy construction without literal K-times leave-one-out coverage recomputation.

For each witness, maintain selected multiplicity `n_w`. A selected frame contributes unique coverage only to witnesses for which `n_w == 1`. Exact unique coverage loss is therefore accumulated from those witnesses directly. Protected-stratum counts and mandatory-obligation ownership are tracked explicitly; extent channels maintain sufficient first/second lower and upper responsibility state to evaluate removal without rescanning the entire subset.

Removal candidates are shortlisted only from negligible-unique-contribution frames with no unique hard obligation/provenance role. Replacement candidates are the union of candidates that can cover current uncovered/bottleneck witnesses, unsatisfied extents, or deficient strata. Exact swap gain is evaluated only for this shortlist. Every accepted swap must strictly improve the frozen lexicographic objective, operate inside the active shell, and inherit the removed frame's rank. A bounded swap/attempt budget limits cost rather than hiding oscillation.

**Acceptance:** restart reproduces the same terminal subset/digest; no lower frozen prefix changes; no hard predicate/coverage component regresses; exact multiplicity-based removal loss agrees with scalar leave-one-out fixtures.

#### Gate TARGET-DATA2C-MVPERF1 - exact-equivalence sparse/incremental performance hardening

**Purpose:** make MVIDX1/MVSEL1/REPAIR1 practical on complete production corpora without changing a single selection decision.

The gate inherits earlier performance authorities:
- PERF-P2/P2R: never recompute work that can be updated/reused from frozen prefix state; persist authenticated reusable stage products;
- PERF-P3/P4: one `StageResourceScope` controls Python processes, native cKDTree workers, BLAS/OpenMP threads, memory budget, and persistence concurrency so nested oversubscription is impossible;
- PERF-P5: stream/hash/persist large arrays without list/concatenate/full-copy transients.

Production optimization may use family-at-a-time KD-tree construction, CSR/CSC/memmap shards, vectorized integer/bitset operations where exact, lazy-greedy upper bounds with exact revalidation, candidate chunking, and deterministic CPU parallelism. Approximate nearest-neighbor/coverage, learned selectors, GPU graph algorithms, or DPP authority are outside this gate unless separately scientifically qualified later.

**Selection-cost authority:** record index/select/repair/audit wall time and CPU-seconds, peak RSS, graph edge count/bytes per edge, number of marginal-gain updates/rescores, witnesses newly covered, repair candidates examined, swaps attempted/accepted, and persistence bytes/time. Full-scale qualification compares scaling against sparse-edge work rather than only one machine's wall time.

**Acceptance:** optimized outputs are byte/decision-equivalent to the simple exact reference on bounded fixtures and exact-check production samples; final selected UID sequence and coverage reports are identical; no locked-test or GPU-specific tuning.

#### Gate TARGET-DATA2C-MVQUAL1 - same-N scientific and learning qualification

**Purpose:** prove that the optimized selector improves or preserves scientific efficiency at identical target cardinality.

A/B legacy versus frozen MV subsets at each common planned `N`. Hard non-regression requires no mandatory, extent, protected-stratum, or previously passing required-view regression. Record

```text
D_max(N) = max_m max(0, 0.95 - C_m(N))
D_sum(N) = sum_m max(0, 0.95 - C_m(N))
N95 = smallest N satisfying all hard predicates
```

plus uncovered mass/count, unique-coverage fraction, zero-unique-contribution fraction, source/correlation diversity, saturation gain, graph/update counts, wall time, and RSS. `D_max` may not worsen relative to legacy at the same N; `D_sum` is secondary. `N95` must not increase on qualification corpora.

Add limited same-N learning controls at one or two common scientifically informative sizes (the smallest common hard-qualified size and optionally the next larger control) under identical TRAIN2/EVAL2 conditions. This guards against a subset that improves geometric coverage while materially degrading learning. Locked tests remain validation-only and cannot tune the selector.

#### Gate SIZE-HALVE2 - coverage-qualified-only successive-fidelity funnel

**Purpose:** integrate the fixed eight possible target sizes with the existing 3/10/30 learning authority without purchasing training for scientifically inadmissible sizes.

Hard coverage qualification occurs before TRAIN2. Let `q` be the number of hard-qualified fixed sizes. `q < 4` fails closed before training/funnel advancement. Only the `q` qualified sizes enter the 3-epoch stage. The survivor counts are:

```text
3 epochs:  q -> min(q, 4)
10 epochs: 4 -> 2
30 epochs: 2 -> 1
```

Thus `q=8` realizes the intended `8 -> 4 -> 2 -> 1`; `q=6` gives `6 -> 4 -> 2 -> 1`; `q=4` gives `4 -> 4 -> 2 -> 1`. Coverage-failing target sizes are never trained merely to fill an eight-candidate bracket.

The gate inherits PERF-P2R continuation/reuse semantics: 3/10/30 evidence comes from uninterrupted training trajectories under the same 30-epoch schedule; completed epochs are not repaid; authenticated DATA8/frame-array products are reused; monitor metrics are derived from already-authorized inference; immutable eliminated-candidate evidence is frozen before optional cache/checkpoint reclamation.

#### Gate SIZE-FIDELITY2 - admission-width and survivor-fidelity requalification

**Purpose:** re-establish early-screen recall after changing both subset geometry and admission width.

Calibrate scientifically available admission widths `q = 4, 5, 6, 7, 8` under uninterrupted full trajectories with halving disabled during qualification. Reconstruct the frozen 3- and 10-epoch decisions retrospectively from the same trajectory and verify the final 30-epoch winners/near-equivalent candidates remain retained. Monitor-size variants remain derived from one authorized inference authority rather than repeated model passes.

#### Gate TARGET-DATA2C-MVMIGRATE1 - generated-policy migration

Migration requirements remain those of revision 65, augmented by revision-66 evidence identities. New generated campaigns adopt the exact sparse MV selector and fixed 16,384 ceiling only after FEAS1 through SIZE-FIDELITY2 pass. Revision-64 rescue remains historical/readable but cannot masquerade as the new authority. Restart invalidation must be minimal and content addressed; valid DATA6/TARGET-DATA2A/B artifacts are reused. e3nn source/DATA6 and CuEq TRAIN2 policy remain orthogonal.

### Final frozen dependency order

```text
TARGET-DATA2C-RESCUE1 (current executable compatibility path)
        |
        v
TARGET-DATA2-MVPLAN2 (this plan-only freeze)
        |
        v
TARGET-DATA2B-FEAS1
        |
        v
TARGET-DATA2C-MVIDX1
        |
        v
TARGET-DATA2C-MVSEL1
        |
        v
TARGET-DATA2C-REPAIR1
        |
        v
TARGET-DATA2C-MVPERF1
        |
        v
TARGET-DATA2C-MVQUAL1
        |
        v
SIZE-HALVE2
        |
        v
SIZE-FIDELITY2
        |
        v
TARGET-DATA2C-MVMIGRATE1
        |
        v
new generated TARGET-DATA2C/D/E authority
```

### Explicit non-goals for this gate sequence

Do not add active AIMD/DFT acquisition, approximate nearest-neighbor authority, learned embeddings/learned subset selection, DPP selection authority, or GPU-resident graph selection while implementing these nine gates. Such alternatives may be benchmarked later only after the exact sparse CPU authority establishes correctness and scaling. Further selector-science changes after this revision require a new explicit architecture revision; performance gates may alter execution only.


## Gate TARGET-DATA2B-FEAS1 - implemented support-fragility and capacity-bound authority (revision 67)

**Implementation status (`0.20.200a0`): implemented and integrated into `prepare` as diagnostic-only evidence. TARGET-DATA2C selector behavior remains revision-64 v4.**

Revision 67 implements the first gate of the revision-66 multi-view roadmap without migrating selection policy. The gate consumes the immutable TARGET-DATA2A development-role freeze and TARGET-DATA2B coverage reference after FOUNDATION-AUDIT1/DATA6 are already frozen. It writes the campaign record `target_coverage_feasibility` and never selects target frames, changes target-size rungs, or accesses locked-test evidence.

### Scientific contract

For every required TARGET-DATA2B family, FEAS1 evaluates the exact witness-specific coverage neighborhood under the same scaled-RMS metric and local radius already frozen by TARGET-DATA2B. Candidate membership is reduced to unique development-frame identities before any diagnostic is accumulated.

FEAS1 records two cross-support views:

1. **self-excluded support** - the witness's own frame is removed, while other frames from the same DATA5 partition unit remain eligible;
2. **correlation-unit-excluded support** - every frame from the witness's own TARGET-DATA2A development interval / DATA5 partition unit is removed.

The second view is the normative fragility diagnostic. Weighted witness mass is recorded for zero support, exactly one supporting candidate, and cumulative candidate-degree bins `<=2`, `<=4`, `<=8`, `<=16`, and `<=32`. A positive required-family zero-support mass above the frozen numerical tolerance yields the diagnostic state `cross_support_fragile`; this state does not itself invalidate current revision-64 selection.

### Conservative cardinality lower bound

For each required family, FEAS1 computes the exact single-candidate coverage gain for every eligible frame from the witness neighborhoods. Let the gains sorted in descending order be `g_(1) >= g_(2) >= ...`. The family lower bound is the smallest `k` for which

```text
sum_{i=1..k} g_(i) >= coverage_threshold.
```

Overlap is deliberately ignored. Because the summed singleton gains are an optimistic upper bound on the union coverage of any `k` candidates, failure of the top `k` singleton gains to reach the threshold proves that no `k`-frame subset can reach it. The result is therefore a valid lower bound, never an optimistic claim of feasibility.

Hard obligations contribute an independent lower bound. Revision 67 includes:

- every required TARGET-DATA2B protected stratum and its `minimum_selected_frames`;
- every required lower/upper extent obligation;
- every TARGET-DATA2A development interval, preserving the current one-frame-per-correlation-interval reservation.

Because development intervals are pairwise disjoint by TARGET-DATA2A contract, the interval count itself is an exact cardinality lower bound. FEAS1 also records total obligation slots, the maximum number of obligation classes satisfiable by one candidate, and the resulting optimistic packing lower bound. The domain-level

```text
K_min_lower_bound = max(required-family coverage lower bounds,
                        hard-obligation lower bound)
```

is compared with the effective ceiling `min(16384, development_frame_count)`. A bound above the ceiling yields `provably_capacity_infeasible` before any MV selector is run.

### State model

Every valid report begins with `self_consistent` and carries exactly one terminal diagnostic state:

- `optimization_required` - no proof of capacity infeasibility and no required-family zero cross-unit support mass;
- `cross_support_fragile` - at least one required family has witness mass that is supported only by its own correlation unit;
- `provably_capacity_infeasible` - the conservative cardinality lower bound exceeds the fixed candidate ceiling.

Self-consistency failures are input/index defects and fail immediately rather than being serialized as a normal state. They include coverage/role domain drift, missing candidate support for a hard extent, invalid protected strata, or broken development-interval coverage.

### Determinism and execution policy

Scientific accumulation is FP64. Neighborhood queries are chunked and may use bounded native cKDTree workers, but worker count and block size are execution-only and excluded from the report identity. Neighbor rows are reduced to sorted unique frame indices before gain/support accumulation, so process/thread scheduling cannot change the report digest.

No persistent `N x N` distance matrix or selector graph is created in this gate. FEAS1 performs bounded exact neighborhood queries and stores only the compact diagnostic report. Exact sparse bidirectional adjacency remains the responsibility of the next gate, TARGET-DATA2C-MVIDX1.

### Campaign integration and restart semantics

`prepare` executes FEAS1 after TARGET-DATA2B and before the existing TARGET-DATA2C ladder. Reuse requires unchanged TARGET-DATA2B reference digest, TARGET-DATA2A role-freeze digest, coverage threshold, and FEAS1 policy digest; otherwise only the diagnostic is rebuilt. The prepare receipt includes `target_coverage_feasibility`. Revision 67 does **not** gate or rewrite TARGET-DATA2C v4; migration remains deferred to TARGET-DATA2C-MVMIGRATE1 after the downstream MV and size-fidelity gates qualify.

### Gate acceptance and next gate

Acceptance requires worker/block-invariant deterministic replay, correct synthetic fragility/capacity diagnostics, production-style TARGET-DATA2B acceptance, serialization/tamper and public-API coverage, regression-clean TARGET-DATA2B/C/D behavior, and synchronized graph/manual status with downstream MV gates still planned.

## Gate TARGET-DATA2C-MVIDX1 - implemented exact sparse bidirectional coverage and hard-obligation substrate (revision 68)

**Implementation status (`0.20.201a0`): implemented and integrated into `prepare` as a diagnostic/index substrate. TARGET-DATA2C selector behavior remains revision-64 v4.**

Revision 68 implements the second gate of the revision-66 optimized multi-view roadmap without changing target selection. MVIDX1 consumes the frozen TARGET-DATA2B coverage reference, TARGET-DATA2A role freeze, and revision-67 FEAS1 authority. It writes `target_coverage_sparse_index` before the existing TARGET-DATA2C v4 ladder and never changes target-size rungs, selected frame identities, the 0.95 hard coverage criterion, TRAIN2 policy, or locked-test isolation.

### Exact required-family sparse graph

For every required TARGET-DATA2B family, MVIDX1 evaluates the same scaled-RMS metric and witness-specific local radius used by the authoritative scorer. Each geometric neighbor row is reduced to its sorted unique development-frame index before an edge is emitted. The scientific relation is therefore exactly:

```text
(witness w) --covers--> (candidate frame c)
iff at least one family element owned by c lies within w's frozen TARGET-DATA2B radius.
```

Each family persists both directions:

```text
witness_offsets + witness_candidates    # witness -> candidate
candidate_offsets + candidate_witnesses # candidate -> witness
```

The first direction makes exact support/coverage checks direct. The inverse is the substrate for MVSEL1 incremental marginal-gain updates: once a witness becomes covered, only candidates adjacent to that witness need their cached gain changed. Arrays use little-endian `uint32` indices and `uint64` offsets; v1 rejects cardinalities outside the exact sparse-transpose range rather than silently widening/reinterpreting the schema. Dense persistent `N x N` distance matrices and persistent Python `set`/`dict` neighbor graphs are forbidden.

The build is family-at-a-time. Exact cKDTree queries may use bounded native workers and fixed-size blocks. Query worker count and block size are execution-only; deterministic reduction to sorted unique frame IDs makes the graph digest invariant to both. The streamed witness-edge build avoids retaining a full Python object graph. Candidate-to-witness adjacency is obtained by deterministic sparse counting transpose.

### First-class hard-obligation index

MVIDX1 separately freezes a generic sparse obligation table with both obligation-to-candidate and candidate-to-obligation directions. It contains:

- required-family lower and upper extent obligations, using the exact TARGET-DATA2B quantile thresholds and candidate frame ownership semantics;
- every TARGET-DATA2B stratum, retaining `required` and `minimum_selected_frames`;
- every TARGET-DATA2A development correlation interval as a required one-frame reservation.

Candidate correlation-unit codes and the sorted immutable interval-unit identities are also persisted. This is deliberately an **index**, not a selector policy: MVSEL1 will decide lexicographic priority among unsatisfied obligations and coverage deficits in the next gate.

### Exact indexed queries and equivalence

The public substrate exposes exact covered-mask/mass, marginal-gain, and obligation-count queries. For a selected candidate set `S`, family coverage is the FP64 sum of reference witness weights whose candidate neighborhood intersects `S`. For candidate `c`, marginal gain is the FP64 weight of currently uncovered witnesses in `candidate_witnesses[c]`. These indexed definitions are required to agree exactly, to numerical summation tolerance, with the existing TARGET-DATA2B authority. MVIDX1 does not replace TARGET-DATA2D as the independent final verifier.

### Authoritative persistence versus reconstructible caches

MVIDX1 scientific evidence is content-addressed independently of future selector execution state. Authenticated native NPY sidecars store the four family adjacency arrays and five domain obligation/unit arrays; the compact JSON manifest binds shape, dtype, byte count, SHA-256, family/frame/upstream digests, policy, obligation metadata, and correlation-unit identities. Large arrays may be restored through memory mapping. Checksum or manifest drift fails closed.

Future MVSEL1/REPAIR1 state such as heaps, marginal-gain vectors, selected masks, multiplicity arrays, repair shortlists, and worker scratch is explicitly reconstructible cache state and must not become MVIDX1 scientific authority. This preserves the revision-66 authoritative-vs-cache persistence split and the streamed-hash/resource-bounding principles inherited from PERF-P3/P5.

### Campaign integration and staged migration

`prepare` now executes TARGET-DATA2B -> FEAS1 -> MVIDX1 -> the unchanged revision-64 TARGET-DATA2C v4 ladder. The prepare receipt includes `target_coverage_sparse_index`. Restart reuse requires unchanged TARGET-DATA2B, TARGET-DATA2A, FEAS1, and MVIDX1 policy identities plus exact persisted forward/inverse consistency; stale/missing graph evidence rebuilds without invalidating valid DATA6/TARGET-DATA2A/B products.

Revision 68 is still pre-migration. The current semi-random/FPS TARGET-DATA2C v4 selector and revision-64 rescue remain executable until MVSEL1, REPAIR1, MVPERF1, MVQUAL1, SIZE-HALVE2, and SIZE-FIDELITY2 all qualify and MVMIGRATE1 explicitly changes generated policy.

### Gate acceptance and next gate

Acceptance requires deterministic worker/block replay; exact forward/inverse adjacency; exact geometric rebuild on deterministic and production-style coverage fixtures; exact covered-mass/marginal-gain agreement with TARGET-DATA2B; hard extent/stratum/correlation indexing; content-addressed native persistence and tamper detection; regression-clean TARGET-DATA2B/C/D; and no current selector/default change.

**Next implementation gate:** `TARGET-DATA2C-MVSEL1` - deterministic two-phase progressive multi-view selector using this exact sparse substrate.



## Gate TARGET-DATA2C-MVSEL1 - implemented deterministic progressive multi-view selector (revision 69)

**Implementation status (`0.20.202a0`): implemented in `prepare` as diagnostic/pre-migration selection evidence; revision-64 TARGET-DATA2C v4 remains the production selector.**

Revision 69 implements the third revision-66 gate on the exact MVIDX1 substrate and writes `target_multi_view_selection` after FEAS1/MVIDX1 but before the legacy ladder. It changes no generated campaign, DATA8 membership, TRAIN2 policy, target-size convergence authority, or locked-test boundary.

### Frozen two-phase objective

MVSEL1 constructs one deterministic ordered coreset through the fixed 16,384 ceiling. FP64 gain accumulation and stable frame UID are frozen. The decision order is:

```text
hard-obligation gain
    -> current worst required-view coverage gain
    -> total newly covered weighted reference mass
    -> least-selected correlation-unit balance
    -> density-aware representative gain
    -> normalized sparse-neighborhood diversity
    -> stable frame UID
```

**Phase A - hard coverage.** Required extent, stratum, and correlation-interval obligations are serviced first. Once those close, the currently worst normalized required family drives selection, followed by total new reference mass. A weighted average cannot compensate for a deficient required view. Phase A ends only when every required family reaches 0.95 and every required obligation passes; otherwise it remains active through the ceiling.

**Phase B - representative filling.** After hard qualification, witness `w` with reference weight `w_w` and selected multiplicity `n_w` contributes the exact marginal utility `w_w / (1 + n_w)` to another candidate covering it. Thus repeated representation has harmonic diminishing return while dense high-mass regions may still receive multiple representatives. Pure maximin/FPS is not the Phase-B authority.

### Exact incremental state

Per required family, reconstructible caches maintain covered witnesses, selected multiplicity, current FP64 coverage mass, candidate uncovered-mass gain, and candidate harmonic gain. When witness state changes, MVIDX1 inverse adjacency updates only adjacent candidates; global candidate-by-witness rescoring after every selection is forbidden. Required-obligation counts/gains use the bidirectional obligation index, and correlation-unit counts provide the provenance tie-break.

The diversity tie-break is intentionally late: it is the mean inverse selected multiplicity over the candidate's indexed witness neighborhoods, unweighted by reference mass. It cannot override hard coverage, weighted representation utility, or provenance balance. Selector masks/gain vectors are reconstructible caches and are not serialized as scientific authority.

### Ordered prefixes, validation, and migration boundary

The scientific record is the ordered UID sequence plus rung evidence. Every materializable rung must equal its exact master-order prefix, contain unique eligible UIDs, preserve lower prefixes, and show non-decreasing binary required-family coverage. Rungs freeze per-family coverage, unsatisfied hard obligations, hard-qualification status, shell coverage/representative gains, and the exact Phase-A closure cardinality when reached.

Validation recomputes persisted rung coverage and hard-obligation counts directly from MVIDX1. Exact replay rebuilds the selector and requires the same digest, providing the reference for MVPERF1 optimization.

`prepare` now executes `TARGET-DATA2B -> FEAS1 -> MVIDX1 -> MVSEL1 -> TARGET-DATA2C v4 -> TARGET-DATA2D/...`, and the prepare receipt includes `target_multi_view_selection`. Upstream/policy drift rebuilds MVSEL1 before the unchanged authoritative v4 ladder. Revision 69 cannot replace `target_data_ladder`, alter DATA8 membership, enter SIZE-HALVE2 training, or change generated defaults.

### Gate acceptance and next gate

Acceptance requires deterministic replay; hard-obligation-first and worst-view behavior; Phase-B harmonic diminishing utility; incremental-gain equality against direct MVIDX recomputation; nested/rung validation; serialization/restart and public-API coverage; regression-clean FEAS1/MVIDX1/TARGET-DATA2C/D behavior; and no production-selector migration.

**Next implementation gate:** `TARGET-DATA2C-REPAIR1` - multiplicity-based exact unique-contribution accounting and deficit-directed active-shell exchange on frozen MVSEL1 prefixes.



## Gate TARGET-DATA2C-REPAIR1 - implemented exact active-shell deficit-directed repair (revision 70)

**Implementation status (`0.20.203a0`): implemented in `prepare` as diagnostic/pre-migration repair evidence; revision-64 TARGET-DATA2C v4 remains the production selector.**

Revision 70 implements the fourth revision-66 multi-view gate after FEAS1, MVIDX1, and MVSEL1. The campaign record is `target_multi_view_repair`. It is built from the immutable TARGET-DATA2B reference, exact MVIDX1 sparse substrate, and MVSEL1 ordered coreset, then the existing revision-64 TARGET-DATA2C v4 ladder is still executed as the production authority. No DATA8 membership, target-size learning candidate, TRAIN2 backend policy, or generated default changes in this gate.

### Exact multiplicity-based redundancy authority

REPAIR1 does not rerun leave-one-out coverage K times. For each required family witness it uses the exact selected multiplicity `n_w` already represented by MVIDX1/MVSEL1 sparse state. A selected candidate contributes unique coverage only when it owns a witness with `n_w == 1`; its exact removal coverage loss is the FP64 sum of those witness weights. The active-shell redundancy telemetry records the fraction of shell frames with effectively zero unique coverage, independently of whether a hard obligation makes a particular zero-unique frame non-removable.

Required extent, protected-stratum, and TARGET-DATA2A correlation-interval counts are exact rather than threshold-capped. Revision 70 therefore makes one internal MVSEL1 cache correction: selected required-obligation multiplicities continue incrementing after the minimum is satisfied, while hard-gain transitions still occur only when the minimum is first reached. This does **not** change any MVSEL1 selection decision or scientific record; it provides the true multiplicity REPAIR1 needs to prove a removal is hard-safe without rescanning the subset.

### Active-shell removal and exact deficit frontier

At each materializable rung `N`, ranks below the preceding materializable rung are frozen. Only the active shell `[previous_N, N)` can supply removal candidates. A removal candidate must satisfy both:

```text
exact unique required-family coverage <= 1e-14
removal does not increase any required-obligation deficit
```

Removal candidates are ordered deterministically by harmonic representative-removal loss, over-represented correlation-unit count, and stable frame UID, then bounded to the frozen v1 reference shortlist. Clustering/neighborhood count is never a removal authority.

Because an admitted removal has zero unique coverage, it cannot lower any required-family coverage component. The exact current MVIDX1/MVSEL1 marginal gains therefore remain valid for replacement coverage. The replacement frontier prioritizes required-obligation deficit reduction when any hard deficit remains, then the current bottleneck-family uncovered mass, then total newly covered mass. If no hard deficit exists and no uncovered mass can be improved, REPAIR1 stops instead of performing arbitrary diversity-only churn.

### Pair-specific representative utility and strict improvement

The Phase-B harmonic objective remains the representation tie-break. If witness `w` has weight `w_w` and selected multiplicity `n_w`, removing a frame covering it loses `w_w / n_w`. For a candidate replacement sharing the removed witness, the add-gain after hypothetical removal changes from `w_w/(n_w+1)` to `w_w/n_w`. REPAIR1 evaluates this pair-specific correction exactly only on sparse shared neighborhoods.

Every accepted swap must strictly improve the lexicographic objective:

```text
1. smaller total hard-obligation deficit
2. larger minimum required-family coverage
3. larger total required-family coverage
4. larger harmonic representative utility
5. better correlation-unit balance
```

No required-family coverage component may regress. Sparse inverse-multiplicity diversity and stable frame UID resolve only later proposal ties; UID remains the final deterministic identity tie-break.

### Rank inheritance, future displacement, and frozen prefixes

The replacement inherits the removed frame's exact rank. If the replacement already exists at a later, not-yet-selected rank in the MVSEL1 master order, the removed frame is moved to that future rank. If the replacement lies outside the planned MVSEL1 prefix, the removed frame leaves the planned order. This preserves a unique repaired master sequence while guaranteeing that no later repair can alter an already-frozen lower prefix.

For every repaired rung, validation requires exact prefix cardinality/UID uniqueness, coverage non-decrease across nested rungs, exact MVIDX1 coverage/obligation recomputation, same-N non-regression relative to MVSEL1, active-shell-only swaps, rank inheritance, swap-budget compliance, and strict persisted improvement. Exact replay may reconstruct the entire authority and must reproduce the same digest.

### Bounded reference policy and MVPERF1 boundary

REPAIR1 v1 is intentionally an exact reference implementation with bounded search: two shell passes, at most 32 accepted swaps per shell, and at most 64 deterministically ordered removal candidates per search iteration. Replacement candidates are not globally pair-enumerated; they are reduced first to the exact hard/coverage deficit frontier. These bounds constrain gate cost without authorizing approximate coverage or approximate swap scoring.

`prepare` now executes `TARGET-DATA2B -> FEAS1 -> MVIDX1 -> MVSEL1 -> REPAIR1 -> TARGET-DATA2C v4 -> ...`, and the prepare receipt includes `target_multi_view_repair`. Upstream or policy drift rebuilds REPAIR1 while preserving valid DATA6/TARGET-DATA2A/B/MVIDX1/MVSEL1 evidence when identities still match.

### Gate acceptance and next gate

Acceptance requires exact unique-contribution agreement with scalar leave-one-out fixtures; exact deselect/select inverse state; strict improvement on deliberately redundant shells; no changes on already-optimal MVSEL1 fixtures; frozen-prefix/rank-inheritance invariants; serialization/restart/tamper/public-API coverage; regression-clean TARGET-DATA2A/B/C/D/E and campaign behavior; and no production selector/default migration.

**Next implementation gate:** `TARGET-DATA2C-MVPERF1` - exact-equivalence sparse/incremental performance hardening of MVIDX1/MVSEL1/REPAIR1.

## Gate TARGET-DATA2C-MVPERF1 - implemented exact-equivalence sparse execution hardening (revision 71)

**Implementation status (`0.20.204a0`): implemented as execution-only hardening of MVIDX1 -> MVSEL1 -> REPAIR1; revision-64 TARGET-DATA2C v4 remains the production selector.**

Revision 71 implements the fifth revision-66 gate without changing any scientific selector policy, ordered frame identity, hard-coverage threshold, repair objective, DATA8 membership, TRAIN2 policy, or generated campaign default. MVPERF1 retains the revision-69/70 scalar implementations as an explicit `reference` execution mode and makes the bounded sparse implementation the default `optimized` mode. `execution_mode` is deliberately excluded from every scientific policy and content digest.

### Exact bounded witness-order sparse scatter

The dominant MVSEL1/REPAIR1 cost was not candidate arbitration but repeated Python/NumPy dispatch while applying one inverse-adjacency update per witness. MVPERF1 preserves the exact witness and per-edge order but groups consecutive complete witness rows into bounded `np.add.at` scatters. The execution-only batch ceiling is 262,144 inverse edges. A witness row is never split solely to meet the ceiling, so ordering and exact row semantics remain unchanged.

For selected witness `w`, the optimized path computes the same scalar FP64 decrement as the reference implementation, in the same witness order, then applies the edge contributions in the MVIDX1 canonical candidate order. The same mechanism is used for REPAIR1 inverse increments during deselection. Exact state tests require equality of availability masks, coverage masks, witness multiplicities, per-family/total coverage gains, per-family/total harmonic representative gains, hard-obligation counts/gains, correlation-unit counts, and persisted plan dictionaries after every qualified update sequence.

This optimization keeps transient memory bounded by sparse batch size rather than total graph size. It does not materialize an `N x N` matrix, does not cast the scientific MVIDX1 arrays to a persistent wider dtype, and does not serialize any execution cache.

### Repair scan consolidation

REPAIR1 previously traversed each active shell once to compute zero-unique telemetry and immediately traversed it again to build the first removal shortlist. MVPERF1 combines those exact queries into one shell pass. Subsequent passes still recompute after an accepted swap because witness multiplicity and hard-safety state may have changed. The optimization therefore removes duplicated work only where state is provably unchanged.

### Resource and persistence policy inherited from PERF-P3/P5

MVIDX1 already uses content-addressed native NPY sidecars, streamed hashing, uint32 sparse indices, uint64 offsets, mmap-backed restore above the frozen threshold, and one family-at-a-time exact neighborhood construction. MVPERF1 retains that layout. MVSEL1 and REPAIR1 now execute inside explicit `StageResourceScope` regions with one Python execution lane and BLAS/native thread limits, preventing nested oversubscription from unrelated OpenMP/BLAS libraries. GPU graph execution and approximate-neighbor authority remain forbidden.

### Candidate arbitration and lazy-heap decision

MVPERF1 benchmarked the remaining vectorized candidate scan rather than automatically replacing it with a lazy heap. On the cardinality stress fixture, candidate arbitration is a minority of total selector runtime while sparse gain maintenance remains dominant. A stale-priority heap would require additional exact tolerance/tie-frontier bookkeeping for hard gain, changing bottleneck family, correlation-unit balance, representative gain, diversity, and stable UID. Because the measured optimized scan is bounded at the frozen <=16,384 selected-cardinality ceiling and preserves simple deterministic semantics, revision 71 does **not** introduce a heap or approximate upper-bound authority. Any later heap implementation must remain exact and prove byte/decision equivalence under the same tie contract.

### Performance qualification evidence

The reproducible MVPERF1 benchmark contains two execution classes. A denser reference-equivalence fixture uses 4,096 candidates, 2,048 selections, three required sparse families, degree 24, and 294,912 sparse family edges. On the revision-71 CPU qualification host the scalar reference selected in about 3.48 s and the optimized implementation in about 1.30 s, a roughly 2.67x selector speedup with the same ordered selection digest and essentially unchanged peak RSS. A cardinality stress fixture with 32,768 candidates and the full 16,384 selections completed the optimized selection loop in about 7.19 s at roughly 269 MiB process peak RSS on a two-family degree-8 sparse graph.

These synthetic graphs are performance fixtures, not scientific tuning data. Scientific acceptance remains exact equivalence on deterministic and production-style TARGET-DATA2B/MVIDX1 fixtures. No locked-test information or GPU-specific performance result participates in the optimization policy.

### Gate acceptance and migration boundary

MVPERF1 acceptance requires byte-identical selector and repair plan dictionaries versus reference execution on qualification fixtures; exact incremental state equality after each tested selection; deterministic scatter ordering and bounded transient edge batches; unchanged MVSEL1/REPAIR1 policy digests; regression-clean TARGET-DATA2A/B/C/D/E and campaign restart behavior; completed 16,384-cardinality stress execution; and no production-selector migration.

`prepare` continues to execute `TARGET-DATA2B -> FEAS1 -> MVIDX1 -> MVSEL1(optimized) -> REPAIR1(optimized) -> TARGET-DATA2C v4 -> ...`. Existing MVSEL1/REPAIR1 records remain valid because execution mode is non-scientific; only missing/stale scientific lineage causes a rebuild.

**Next implementation gate:** `TARGET-DATA2C-MVQUAL1` - same-N independent scientific A/B qualification of the frozen optimized MV selector/repair against the current production selector.


## Gate TARGET-DATA2C-MVQUAL1 - implemented independent same-N scientific qualification (revision 72)

**Implementation status (`0.20.205a0`): implemented as pre-migration scientific A/B evidence; revision-64 TARGET-DATA2C v4 remains the production selector and positive legacy-vs-MV TRAIN2 controls remain deferred to the final consolidated GPU qualification.**

Revision 72 implements the sixth revision-66 gate. MVQUAL1 consumes immutable TARGET-DATA2B, FEAS1, DATA2A, MVIDX1, the optimized REPAIR1 authority, and the current legacy TARGET-DATA2C v4 ladder. It does not construct a new training dataset. Its purpose is to determine whether the frozen MV selector is scientifically at least as efficient as the current selector at the same cardinality before SIZE-HALVE2 is allowed to integrate it into the learning funnel.

### Independent coverage authority

For each label domain and every target size materializable by both selectors, MVQUAL1 rebuilds two `TargetCoverageReport` objects by calling the immutable TARGET-DATA2B scorer on the legacy and repaired-MV frame identities. Persisted MVSEL1/REPAIR1 family coverage cannot satisfy the gate. The exact MVIDX1 covered mass is recomputed only as secondary telemetry and must agree with the independent TARGET-DATA2B result within `5e-12`; disagreement is an input/authority error.

Required DATA2A/MVIDX1 hard obligations are evaluated separately because TARGET-DATA2B `TargetCoverageReport` does not encode every correlation-interval reservation. Therefore same-N hard non-regression covers all of the following:

```text
required-family 0.95 coverage
required lower/upper extent predicates
required protected strata
required MVIDX1/DATA2A obligations, including correlation intervals
```

A predicate that fails for both selectors is diagnostic, not a regression. A predicate that passes for legacy and fails for MV is a hard MVQUAL1 failure.

### Worst-view deficit and N95 authority

For every common target size `N`, define

```text
D_max(N) = max_m max(0, 0.95 - C_m(N))
D_sum(N) = sum_m max(0, 0.95 - C_m(N))
```

where `m` spans required TARGET-DATA2B families and `C_m` is independently rescored covered reference mass. Same-N acceptance requires

```text
D_max_MV(N) <= D_max_legacy(N) + 1e-12
```

at every common materializable N. `D_sum` is recorded as a secondary aggregate-deficit diagnostic and cannot compensate for a worse bottleneck family.

`N95_common` is the smallest common N for which every label domain passes independent TARGET-DATA2B plus required DATA2A/MVIDX1 obligations. If legacy has a finite `N95_common`, MV must also have one and it may not be larger. If legacy never qualifies on the common set, MV is not penalized for qualifying at a size unavailable to the legacy comparison.

### Redundancy, uncovered-support, and provenance telemetry

For both selectors and every common N, MVQUAL1 records exact sparse telemetry without allowing it to override the independent pass authority:

- uncovered witness count and total uncovered reference mass;
- fraction of required-family reference mass having exactly one selected representative;
- fraction of selected candidates with zero unique required-family witness ownership;
- number of represented DATA2A/MVIDX1 correlation units and maximum correlation-unit share;
- number of represented development runs and conditions.

Witness multiplicities are recomputed from the persisted MVIDX1 graph. These metrics expose whether an apparent coverage result was purchased through redundant local clustering or loss of provenance diversity, but only hard predicates, `D_max`, and `N95_common` determine MVQUAL1 pass/fail.

### Independent ceiling diagnosis

Same-N comparison is limited to target sizes available to both selectors, but capacity diagnosis is not. Every materializable MV rung is independently rescored through TARGET-DATA2B plus hard obligations, including the 16,384 rung when present. `mv_qualified_sizes` therefore cannot inherit or trust REPAIR1's internal `hard_coverage_qualified` flag.

The diagnostic outcomes are:

- `coverage_qualified_within_ceiling`
- `capacity_limited_within_16384`
- `provably_capacity_infeasible`
- `incomplete_ceiling_evidence`

The provable-infeasibility outcome is inherited only from FEAS1's optimistic lower-bound proof. The capacity-limited outcome requires independent evidence that a materializable 16,384 MV subset still fails while FEAS1 has not already proved infeasibility. No outcome authorizes expansion beyond 16,384.

### Learning-control freeze and final-GPU policy

MVQUAL1 freezes at most two common target sizes at which **both** selectors independently satisfy all hard predicates, preferring the smallest common qualified size and then the next larger common qualified control. These sizes become the required legacy-vs-MV TRAIN2/EVAL2 learning controls so that improved geometric coverage cannot silently degrade learning behavior.

Positive TRAIN2 execution is not performed in this gate on the development host. The record freezes `learning_control_status = deferred_final_gpu_qualification`, preserving the project-wide policy that positive GPU qualification is executed once on the user's final complete package. Locked-test data remain validation-only and cannot tune selector policy or MVQUAL thresholds.

### Campaign integration and migration boundary

The campaign record is `target_multi_view_qualification` and is part of the prepare restart receipt. Its scientific identity binds TARGET-DATA2B, FEAS1, DATA2A, MVIDX1, the legacy TARGET-DATA2C ladder, REPAIR1, and MVQUAL1 policy. Any identity drift invalidates only this downstream qualification evidence.

`prepare` now executes

```text
TARGET-DATA2B -> FEAS1 -> MVIDX1 -> MVSEL1 -> REPAIR1
              -> TARGET-DATA2C v4 -> MVQUAL1 -> TARGET-DATA2D -> ...
```

MVQUAL1 may record a failed experimental selector without breaking the legacy production campaign because revision-64 TARGET-DATA2C v4 remains authoritative until MVMIGRATE1. No DATA8 membership, TARGET-DATA2D survivor policy, TRAIN2 backend, e3nn/CuEq phase split, or generated default changes in revision 72.

### Gate acceptance and next gate

Acceptance requires deterministic round-trip/replay; independent TARGET-DATA2B rescore rather than selector-internal pass reuse; exact hard-obligation non-regression; non-worse same-N `D_max`; non-increasing common `N95`; exact MVIDX/TARGET-DATA2B mass cross-check; independent all-MV-rung capacity rescoring; frozen learning-control sizes; campaign restart/receipt integration; and regression-clean upstream multi-view stages plus TARGET-DATA2C/D behavior.

**Next implementation gate:** `SIZE-HALVE2` - integrate the fixed eight possible target sizes with coverage-qualified-only `q -> min(q,4) -> 2 -> 1` successive fidelity at 3/10/30 epochs.

## Gate SIZE-HALVE2 - fixed-eight qualified-only funnel implemented (revision 73)

**Implementation status (`0.20.206a0`): implemented as a pre-migration control-plane authority. Revision-64 TARGET-DATA2C v4 and TARGET-DATA2D v2 remain the current production path until SIZE-FIDELITY2 and MVMIGRATE1 close.**

Revision 73 implements the seventh gate of the optimized multi-view target-data roadmap. The new `mdstats.size-halve2-plan.v1` authority consumes the immutable REPAIR1 plan and the independent MVQUAL1 result. It freezes exactly eight possible target cardinalities:

```text
128, 256, 512, 1024, 2048, 4096, 8192, 16384
```

No dynamic rescue size may enter this authority. For each fixed size the record binds every repaired-domain rung digest, global materializability, and the independently hard-qualified MVQUAL1 state. The scientific input is therefore the independently rescored MV population rather than the selector's internal coverage telemetry.

### Hard admission before training

Let `q` denote the number of independently hard-qualified fixed sizes. The new funnel is fail-closed before TRAIN2 when `q < 4`. Coverage-failing or unavailable sizes are never inserted merely to complete an eight-entry bracket and cannot purchase a 3-epoch run. MVQUAL1 same-N and N95 non-regression must also pass before the future funnel is work-authorizing. While pre-migration, a blocked SIZE-HALVE2 record is diagnostic and does not break the still-active legacy DATA2C/DATA2D campaign path.

For an admissible population, the survivor geometry is exactly:

```text
epoch 3:   q -> min(q, 4)
epoch 10:  4 -> 2
epoch 30:  2 -> 1
```

Thus `q=8` realizes `8 -> 4 -> 2 -> 1`; `q=6` realizes `6 -> 4 -> 2 -> 1`; and `q=4` realizes `4 -> 4 -> 2 -> 1`. The epoch-3 stage requires exactly the hard-qualified population and rejects extra evidence from a coverage-failing size. At least four numerically valid candidates must remain after the coarse endpoint; otherwise the future MV funnel fails rather than silently changing its calibrated width.

### Exact uninterrupted continuation

SIZE-HALVE2 reuses the existing `TargetSizeTrainingEvidence` and PERF-P2R work geometry. A candidate is initialized once on the nominal 30-epoch schedule. Promotions are exact continuations:

```text
0 -> 3 epochs:  hard-qualified candidates only
3 -> 10 epochs: four epoch-3 survivors
10 -> 30 epochs: two finalists
```

Epoch-10 evidence must authenticate the exact epoch-3 checkpoint, optimizer, and RNG parent. Epoch-30 evidence must authenticate the exact epoch-10 checkpoint, optimizer, and RNG parent, and foundation/evaluation-role/TRAIN2-policy/training-run/schedule identity cannot change across the continuation. Normalized schedule progress must be exactly 3/30 and 10/30 at the early endpoints, and optimizer-update plus structure-exposure counts must strictly increase across each promotion. Completed epochs are therefore never repaid. PERF-P2R stage plans generated from SIZE-HALVE2 carry the same incremental epoch boundaries and continuation flags as the existing production control plane.

### Ranking and boundary semantics

The existing deterministic target-force ranking and practical-equivalence rules are retained. At epochs 3 and 10, the largest independently hard-qualified fixed size is moved to the front only within its own practical-equivalence band; it receives no protection against a materially better earlier band. This preserves bounded-ladder convergence sensitivity.

At epoch 30, final selection returns to the smaller-size preference within practical equivalence and applies the full target/replay/physical admissibility contract. If the largest independently hard-qualified fixed size is a finalist and remains materially better than its smaller admissible finalist by more than the frozen practical-equivalence width, the outcome is `nonconverged_at_fixed_ceiling` rather than a false convergence claim. The ceiling remains exactly 16,384.

### Persistence and migration boundary

Campaign `prepare` now builds/reuses `size_halve2_plan` after `target_multi_view_qualification` and binds it into the prepare receipt. The record is content-addressed to REPAIR1, MVQUAL1, the fixed eight-size policy, and all repaired-rung identities. It remains evidence for SIZE-FIDELITY2/MVMIGRATE1 only; DATA8 membership and TARGET-DATA2D shortlists are unchanged. **Next gate:** `SIZE-FIDELITY2`, calibrating `q=4..8` survivor recall from uninterrupted 30-epoch trajectories; positive GPU execution remains deferred to final consolidated qualification.

## Gate SIZE-FIDELITY2 - admission-width survivor requalification implemented (revision 74)

**Implementation status (`0.20.207a0`): implementation-complete pre-migration control plane; positive MACE/GPU calibration remains deferred to `FINAL-GPU1`. Revision-64 TARGET-DATA2C v4 and TARGET-DATA2D v2 remain the current production path until MVMIGRATE1 explicitly changes generated policy.**

Revision 74 implements the eighth gate of the optimized multi-view target-data roadmap. The new `mdstats.size-fidelity2-execution-plan.v1` authority consumes the pre-migration SIZE-HALVE2 plan and freezes the exhaustive empirical work needed to prove that the new q-dependent early screens do not discard candidates that matter at full fidelity.

### One exhaustive trajectory matrix for every q width

Let `q_max` be the number of independently hard-qualified SIZE-HALVE2 candidates. The qualified nested population must be a contiguous suffix of the fixed ladder

```text
128, 256, 512, 1024, 2048, 4096, 8192, 16384
```

and the scientifically available admission-width surface is exactly every `q` in `4..q_max`. Calibration **does not** execute a separate training campaign for each q. For each frozen optimizer seed, every hard-qualified size is initialized once on the common nominal 30-epoch schedule and continued uninterrupted to epoch 30 with halving disabled. Checkpoints at epochs 3, 10, and 30 provide all evidence needed to retrospectively reconstruct every available q-width funnel.

Consequently the training-run count is

```text
N_runs = N_seeds * q_max
```

rather than `N_seeds * sum(q)`. For the full q=8 surface and the frozen three calibration seeds, SIZE-FIDELITY2 requires 24 uninterrupted training trajectories and 72 authorized full prediction products. This directly carries forward the PERF-P2/P2R rule that reusable scientific work is computed once and sliced/replayed rather than repaid.

### Exact uninterrupted 3/10/30 authority

Each trajectory must prove exact continuation rather than restarted short jobs. Epoch 10 authenticates the epoch-3 checkpoint, optimizer state, and RNG state; epoch 30 authenticates the epoch-10 parent. Foundation identity, evaluation-role identity, TRAIN2 policy, training-run identity, and schedule identity remain constant for one trajectory and the common scientific identities remain fixed across the full matrix. Normalized schedule progress is exactly `3/30`, `10/30`, and `30/30`; optimizer updates and presented-structure counts increase strictly at each continuation.

The execution plan is therefore sufficient for FINAL-GPU1 to schedule one uninterrupted trajectory per `(seed, target_size)` and derive every q-width decision without duplicate training.

### Hard finalist-recall criterion

For each seed and admission width, the **complete epoch-30 population** defines the reference two finalists under the same deterministic practical-equivalence ordering used by SIZE-HALVE2. The early stages are then reconstructed from the stored full trajectories:

```text
epoch 3:   q -> min(q, 4)
epoch 10:  4 -> 2
epoch 30:  full q population remains available only for calibration truth
```

Both eventual epoch-30 finalists must be retained by the reconstructed epoch-3 stage and again by the epoch-10 stage. Required finalist recall is `1.0` at both boundaries for every frozen seed and every scientifically available q. Winner recall is recorded as a diagnostic, but it cannot substitute for retaining both final candidates: one false elimination is scientifically sufficient to reject the coarse screen even when global rank correlation is high.

The fixed ceiling is also requalified. If the 16,384 boundary is the epoch-30 winner and its target-force score remains better than every smaller admissible candidate by more than the frozen practical-equivalence width, that calibration seed/q combination records boundary nonconvergence and SIZE-FIDELITY2 fails. The bounded 16,384 ladder may not be declared converged merely because the early-screen recall is correct.

### Monitor-size calibration without repeated inference

SIZE-FIDELITY2 inherits the prior SIZE-FIDELITY1 monitor grid

```text
128, 256, 512, 1024 configurations
```

but tightens its provenance. Every monitor score is a deterministic view derived from the **same authorized epoch-3 full prediction product** for that `(seed, target_size)` checkpoint. The monitor record carries that full-prediction digest and is rejected if the lineage differs. Epoch-10 and epoch-30 checkpoints cannot request separate monitor inference.

Therefore monitor calibration adds exactly **zero model-inference passes**. For each candidate monitor size, the epoch-3 promotion set is reconstructed and compared with the full-role promotion set across every seed and q width. The recommended monitor is the smallest candidate with exact promotion-set equivalence and complete eventual-finalist retention throughout the calibration surface.

### Campaign persistence and final-GPU boundary

Campaign `prepare` now builds/reuses `size_fidelity2_execution_plan` immediately after `size_halve2_plan` and includes it in the prepare restart receipt. A ready SIZE-HALVE2 plan yields the exact GPU-deferred work matrix. A blocked SIZE-HALVE2 plan yields a content-addressed blocked/no-work SIZE-FIDELITY2 record; it does not interrupt the active legacy production path.

The qualification-report schema is implemented and deterministic, including round-trip/recompute validation, but no synthetic fixture is permitted to masquerade as production accelerator evidence. The development-host release therefore records positive GPU execution as `deferred_final_gpu_qualification`. FINAL-GPU1 remains responsible for the release-matched real MACE trajectories, survivor-recall result, monitor recommendation, and whole-funnel evidence.

### Gate acceptance and migration boundary

Implementation acceptance requires: exact q=4..8 policy serialization; adaptive available-width planning for q=4..8; single-matrix training reuse; zero-additional-inference monitor derivation; exact 3/10/30 ancestry and identity checks; deterministic retrospective ranking; hard 100% two-finalist recall at epochs 3 and 10; fixed-ceiling nonconvergence rejection; blocked/no-work behavior; campaign receipt/restart integration; and regression-clean SIZE-HALVE2/SIZE-FIDELITY1/campaign behavior.

This gate changes no production target membership or generated defaults. Revision-64 TARGET-DATA2C v4, TARGET-DATA2D v2, DATA8 membership, the 0.95 coverage threshold, source-side e3nn policy, and TRAIN2 CuEq policy remain unchanged.

**Next implementation gate:** `TARGET-DATA2C-MVMIGRATE1` - explicit generated-policy migration to the exact sparse MV selector/fixed 16,384 ladder, gated by the required qualification evidence and preserving the final consolidated GPU-qualification policy.


## Gate TARGET-DATA2C-MVMIGRATE1 - implemented atomic migration latch (revision 75)

**Implementation status (`0.20.208a0`): implementation-complete control plane; activation remains deferred to `FINAL-GPU1` by the project-wide consolidated GPU-qualification rule. Revision-64 TARGET-DATA2C v4 / TARGET-DATA2D v2 / TARGET-DATA2E v2 remain the live generated production path until final GPU evidence authorizes one atomic promotion.**

Revision 75 implements the migration boundary frozen in revisions 65-66 without weakening the prior evidence chain. `TargetMultiViewMigrationPlan` binds the legacy v4 ladder, REPAIR1, MVQUAL1, SIZE-HALVE2, and SIZE-FIDELITY2 execution identities into one content-addressed latch. Scientific failures yield `blocked_scientific_preconditions`; otherwise absent final-GPU evidence yields `awaiting_final_gpu_qualification`; only positive final evidence yields `authorized_for_atomic_activation`.

The migrated candidate family is explicitly generation-separated:

```text
TARGET-DATA2C v5 -> TARGET-DATA2D v3 -> TARGET-DATA2E v3
```

TARGET-DATA2C v5 freezes exactly `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`, uses only prefixes of the REPAIR1 `repaired_master_order`, independently reconstructs TARGET-DATA2B coverage and TARGET-DATA2A hard-obligation evidence, requires four hard-qualified sizes before TRAIN2, and has no dynamic upper-ladder rescue. v4 remains readable/auditable but cannot deserialize or validate as v5. TARGET-DATA2D v3 is bound only to v5 and freezes `min_coverage_qualifiers = 4`; TARGET-DATA2E v3 is likewise bound only to the migrated C/D generation and requires the migration provenance needed to reauthenticate v5.

### Final-GPU activation predicates

Generated-default promotion is fail-closed until all of the following are true:

1. MVQUAL1 same-N hard-predicate/Dmax and common-N95 non-regression pass.
2. At least four MV fixed sizes independently satisfy the hard coverage authority.
3. SIZE-HALVE2 is `ready_for_size_fidelity2`.
4. SIZE-FIDELITY2 is `ready_for_final_gpu_calibration`.
5. The frozen MVQUAL1 same-N learning-control sizes have paired legacy-vs-MV TRAIN2/EVAL2 evidence under an identical training-protocol digest, with the MV force score not materially worse than legacy beyond the frozen practical-equivalence width.
6. SIZE-FIDELITY2 qualification passes and `gpu_qualification_status == "passed"`.

A deferred CPU/control-plane SIZE-FIDELITY2 report is not sufficient. This is intentional: revision 75 prepares the complete migration transaction while preserving the decision to perform GPU qualification once, against the complete final package.

### Restart/cost contract

Campaign `prepare` now persists `target_multi_view_migration_plan`. When scientific preconditions allow it, it also materializes `target_data_ladder_mv_candidate`, an authenticated v5 candidate bound to the migration-plan digest. Updating final-GPU evidence invalidates only the migration latch/candidate boundary. Unchanged DATA6, TARGET-DATA2A/B, FEAS1, MVIDX1, MVSEL1, REPAIR1, and MVQUAL1 evidence remains reusable; no valid expensive upstream evidence is repaid.

The live `target_data_ladder` record remains v4 in this release. Atomic replacement with v5, followed by D v3/E v3 generation, is a final-release transaction and may occur only after the latch authorizes activation. This avoids partially migrated restart state.

No DATA8 membership, 0.95 coverage threshold, e3nn source/DATA6 policy, CuEq TRAIN2 policy, or revision-66 selector science changes in revision 75.

**Next release action:** execute the consolidated `FINAL-GPU1` qualification package on the user's GPU system; if all required evidence passes, atomically promote TARGET-DATA2C/D/E to v5/v3/v3.
