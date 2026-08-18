---
title: "MLFF PERF-P2R CPU/Control-Plane Benchmark"
version: "0.20.184a0"
date: "2026-08-15"
status: "bounded CPU implementation evidence; no GPU claim"
---

# Scope

This benchmark measures the CPU/control-plane portion of PERF-P2R. It does **not** execute MACE training or inference and therefore does not close whole-funnel performance qualification.

The timed path is the authenticated DATA8 immutable fixed-file cache on the deterministic DATA8 regression fixture. The successive-fidelity work accounting follows the resource-allocation principle of successive halving.[^jamieson2016] The same DATA8 authority is rebuilt at the same output path for every sample. Fifteen fresh builds are compared with fifteen cache-hit builds after one cache-population pass.

# DATA8 fixed-file cache

| Metric | Fresh construction | Authenticated cache hit |
|---|---:|---:|
| Samples | 15 | 15 |
| Median wall time | 79.696 ms | 17.333 ms |
| Observed range | 76.212--84.553 ms | 16.105--20.481 ms |
| Median process CPU | 61.923 ms | 17.325 ms |
| Median write characters | 204,478 | 80,429 |
| Median read characters | 641,416 | 157,667 |

The median cache-hit wall time is **4.598x faster**, a **78.25% reduction** on this bounded fixture. Cache population took 105.047 ms. The cache contained 11 authenticated generations, 33 files, and 152,891 bytes.

Every cache-hit `Data8PreparationBundle.to_dict()` was exactly equal to the fresh reference authority. The result therefore qualifies the implementation hot path, not a new scientific representation.

# Successive-fidelity exposure

For admitted sizes $A$, coarse survivors $S_4$, short finalists $S_2$, and coarse boundary $e_0$,

$$
W=e_0\sum_{i\in A}K_i +(10-e_0)\sum_{i\in S_4}K_i +20\sum_{i\in S_2}K_i.
$$

For all seven default sizes, the exact exposure envelope is:

| Coarse boundary | Smallest-size survivors | Saved vs. exhaustive | Largest-size survivors | Saved vs. exhaustive |
|---:|---:|---:|---:|---:|
| 3 epochs | 69,888 | 85.67% | 402,048 | 17.56% |
| 4 epochs | 84,224 | 82.73% | 402,944 | 17.38% |
| 5 epochs | 98,560 | 79.79% | 403,840 | 17.19% |

The benchmark record also enumerates ladder widths 3 through 7 for all three coarse boundaries. These values are exact structure-epoch work counts. They are **not wall-time predictions**.

# Interpretation

PERF-P2R removes redundant fixed-file construction and makes training work incremental across stage boundaries. The measured CPU cache benefit is large on the development fixture, while the analytical exposure bound confirms that the corrected halving rule still provides meaningful work reduction even when the largest candidates survive.

No GPU, VRAM, utilization, MACE throughput, or resumed-versus-uninterrupted endpoint claim is made here. Those measurements remain consolidated in FINAL-GPU1.

# Reproduction

```bash
python benchmarks/benchmark_mlff_perf_p2r.py \
  --repeats 15 \
  --output benchmarks/mlff_perf_p2r_cloud_cpu_2026-08-15.json
```

The JSON record is the machine-readable authority for the numbers above.

[^jamieson2016]: Kevin Jamieson and Ameet Talwalkar, "Non-stochastic Best Arm Identification and Hyperparameter Optimization," *Proceedings of Machine Learning Research* 51, 240--248 (2016), https://proceedings.mlr.press/v51/jamieson16.html.
