# PERF-BASE0 same-host reproducibility comparison

- Scientific match: **True**
- Scientific digest: `44a5aa8b492cece8d303f83a163ddbeee6d3a340932d4716c53b4ddf28a81e3c`
- Run 1 execution digest: `2c7614fea8dc60594e176e7c4fa17413922c56d67982e881a8fab0eebbc5b18c`
- Run 2 execution digest: `0d3649ed0dfdb92e3daddb8a7d9a5361b591e0f1e1069156a602afb019fec564`
- Comparison digest: `c3d31a3922c89d19cc9a5670b9b4ca8f7ffaa65f82cffa8c16a25c0fb50d5e9e`

| Stage | Run 1 wall (s) | Run 2 wall (s) | Run2/Run1 | Run 1 CPU (s) | Run 2 CPU (s) | Run1 peak RSS (MiB) | Run2 peak RSS (MiB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `adversarial_geometry_statistics` | 0.002331 | 0.002169 | 0.931 | 0.002403 | 0.002083 | 542.07 | 541.90 |
| `compact_regression` | 0.002670 | 0.003227 | 1.208 | 0.002727 | 0.003303 | 542.07 | 541.89 |
| `input_identity` | 1.284392 | 1.270114 | 0.989 | 1.296955 | 1.279607 | 259.10 | 259.00 |
| `replay_ingest` | 7.300726 | 8.454639 | 1.158 | 7.361805 | 8.522987 | 527.34 | 527.16 |
| `target_data2b_exact_radii` | 5.518176 | 6.264822 | 1.135 | 24.194879 | 25.369443 | 559.38 | 563.02 |
| `target_data2c_exact_fps` | 6.018641 | 9.599687 | 1.595 | 40.434348 | 68.954691 | 561.04 | 563.39 |
| `training_ingest` | 131.846106 | 117.054367 | 0.888 | 134.663969 | 118.204730 | 527.31 | 527.14 |

The exact corpus and scientific-stage authorities are byte/digest identical. The observed timing spread is therefore execution noise and is retained as the initial same-host variability envelope for later performance gates.
