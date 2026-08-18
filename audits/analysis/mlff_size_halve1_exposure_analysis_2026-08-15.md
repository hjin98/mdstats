---
title: "MLFF SIZE-HALVE1 Work-Exposure and Optimization-Coverage Analysis"
subtitle: "CPU-testable planning evidence for the corrected 3/10/30 target-size funnel"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.8in
toc: true
toc-depth: 2
numbersections: true
fontsize: 10pt
---

# Scope

This report evaluates the corrected target-size funnel without claiming MACE/GPU training performance. Coverage is hard admission only; all qualified sizes enter the 3-epoch screen. The exposure model is exact for structure-epoch counts under the frozen 3/10/30 policy, but it is not a wall-time model.

# Frozen funnel

$$
N_{\mathrm{eligible}} \xrightarrow{3\ \mathrm{epochs}} \le 4 \xrightarrow{10\ \mathrm{epochs}} 2 \xrightarrow{30\ \mathrm{epochs}} 1.
$$

Policy digest: `49bf6d52e0ce78eb06176f14d534afb6d016179e9b90d7696a752f8bb49cb4f8`.

The target structure-epoch exposure proxy is

$$
W = 3\sum_{i\in A}K_i + 7\sum_{i\in S_4}K_i + 20\sum_{i\in S_2}K_i,
$$

relative to

$$
W_{\mathrm{full}} = 30\sum_{i\in A}K_i.
$$

# Exposure envelope

The table enumerates monotone suffixes of the default nested ladder, from the minimum three qualifiers through all seven. `Best` means the smallest permitted survivors continue; `worst` means the largest permitted survivors continue.

| Qualifiers | Eligible sizes | Best reduction | Worst reduction |
|---:|---|---:|---:|
| 3 | 2048, 4096, 8192 | 38.10% | 9.52% |
| 4 | 1024, 2048, 4096, 8192 | 53.33% | 13.33% |
| 5 | 512, 1024, 2048, 4096, 8192 | 72.26% | 15.81% |
| 6 | 256, 512, 1024, 2048, 4096, 8192 | 81.27% | 16.98% |
| 7 | 128, 256, 512, 1024, 2048, 4096, 8192 | 85.67% | 17.56% |

With all seven default sizes admitted, the exposure reduction is bounded between **17.56%** and **85.67%**, depending on which sizes survive. This wide range is why PERF-P2R must benchmark both unfavorable large-size-survivor and favorable small-size-survivor cases rather than report one convenient path.

# Required qualification additions

1. **SIZE-FIDELITY1 before performance promotion.** Exhaustively continue all hard-coverage qualifiers to 30 epochs for multiple screening seeds; retrospectively test epoch-3 top-four and epoch-10 top-two recall of the eventual 30-epoch winner/finalists.
2. **Coarse-monitor calibration.** Compare the fixed coarse role against the full development role at epoch 3 and choose the smallest monitor that preserves promotion decisions up to practical equivalence. The current 256-frame setting is provisional.
3. **Early-equivalence calibration.** Calibrate the coarse practical-equivalence width from real trajectory/seed variability. A tied largest boundary is preserved within its band so bounded-ladder nonconvergence remains observable.
4. **Sampler-aware continuation.** Exact 3->10->30 continuation must include DataLoader/sampler/worker ordering state or prove deterministic epoch-boundary reconstruction, in addition to model, optimizer/scheduler, and global RNG state.
5. **Worst-case performance matrix.** PERF-P2R must cover 3, 4, 5, 6, and 7 admitted sizes and both small-survivor and large-survivor extremes, plus single- and multi-GPU resource regimes where available.
6. **Fuse execution, not authority.** Boundary evaluation may run in the same process as training to avoid checkpoint reload only when it emits the same separate EVAL2 scientific evidence. Shared graph/preprocessing caches and nested prefix manifests must remain byte/array equivalent.
7. **Checkpoint-I/O control.** Full restart authority is mandatory at epochs 3, 10, and 30. Additional recovery checkpoints may use a bounded execution-only cadence and may be reclaimed after immutable elimination evidence is frozen.

# Environment and limitation

This analysis ran under `AMD EPYC 9V74 80-Core Processor` with cgroup CPU limit `800000 100000` and memory limit `4294967296`. No authorizing MACE runtime/checkpoint or GPU was available. Therefore no epoch-3/10/30 wall-time, GPU-utilization, VRAM, or survivor-fidelity claim is made here.

# References

The staged budget-allocation pattern is related to successive-halving and Hyperband, but mdstats keeps its own deterministic scientific metrics, hard coverage gate, exact continuation, and provenance contract.

1. Kevin Jamieson and Ameet Talwalkar, *Non-stochastic Best Arm Identification and Hyperparameter Optimization*, PMLR 51, 2016. [PMLR article](https://proceedings.mlr.press/v51/jamieson16.html).
2. Lisha Li, Kevin Jamieson, Giulia DeSalvo, Afshin Rostamizadeh, and Ameet Talwalkar, *Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization*, JMLR 18(185), 2018. [JMLR article](https://www.jmlr.org/papers/v18/16-558.html).
