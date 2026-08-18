# LD7 full-trajectory benchmark

## Configuration

- Input: first **1,300** frames of `TRAJECTORY(3)` at **1 fs**.
- Registration: framework-registered Na-LTA primitive cell.
- Density samples: every one of the 1,300 frames.
- Spread estimate: **128** deterministic stratified-random temporal frames, seed 0.
- Adaptive target: effective artificial RMS / 10th-percentile positional SD <= 0.5.
- Kernel: `discrete_periodized_v1`, tail tolerance `1e-3`.
- Storage: `local_sparse`, block shape `(16, 16, 16)`.
- Execution: pair chunk 262,144; source-group batch size 8.
- Workspace limit: 4 GiB.

## Results

| Species | Resolved grid | Preparation time | Cumulative kernel pairs | Stored slots | Retained field | Integral |
|---|---:|---:|---:|---:|---:|---:|
| Na | `(525, 525, 525)` | 13.745 | 96,251,957 | 3,084,288 | 26.49 MiB | 24 |
| Si | `(1121, 1121, 1121)` | 33.420 | 164,431,073 | 3,641,344 | 27.80 MiB | 24 |
| Al | `(1038, 1038, 1038)` | 16.556 | 158,246,794 | 3,481,600 | 26.58 MiB | 24 |
| O | `(690, 690, 690)` | 60.151 | 558,840,991 | 14,725,120 | 126.47 MiB | 96 |

Total density-preparation time: **125.278 s**.

Total cumulative kernel pairs: **977,770,815**.

The benchmark includes adaptive-resolution diagnostics, all-frame CIC deposition, canonical sparse convolution, deterministic source-group batching, exact batch merging, and production block packing. It excludes isosurface extraction and browser serialization.

## Interpretation

The pre-LD7 implementation could not evaluate the oxygen field under the same memory limit because temporary pair arrays scaled with all approximately 560 million pairs. LD7 keeps the realized scatter workspace near 45--52 MiB per field in this benchmark and preserves exact integrated measures.
