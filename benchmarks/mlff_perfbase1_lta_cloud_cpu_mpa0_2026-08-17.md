# MLFF PERFBASE1 reproducible performance baseline

- Baseline ID: `lta-perfbase1-cloud-cpu-mpa0-2026-08-17`
- mdstats source: `0.20.225a0`
- Foundation: `mace-mpa-0` / `medium`
- Foundation SHA-256: `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`
- Scientific digest: `d16fdb3a52112192789a27f1515380ec29e8ac278e70b6b0bf669753a77e39df`
- Execution digest: `a431a0d611d2fb7be855a1daa9a901cb90434bc054ddb03d6bc896d64ee6a597`
- Content digest: `5b8e1d8315cc103d317fd6bb8948bf8f699ef834873e9d2b1983345536d32ece`

## Workload summaries

| Workload | Schedule | Workers | Repeats | Median wall (s) | Wall CV | Median occupancy | Peak RSS (MiB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `target_data2b_reference_radii` | `serial` | 1 | 2 | 0.612311 | 0.0559 | 1.0332 | 261.14 |
| `target_data2b_reference_radii` | `dual` | 2 | 2 | 0.457473 | 0.0404 | 0.6862 | 261.44 |
| `target_data2b_reference_radii` | `intermediate` | 2 | 2 | 0.457473 | 0.0404 | 0.6862 | 261.44 |
| `target_data2b_reference_radii` | `auto` | 3 | 2 | 0.423369 | 0.1774 | 0.5129 | 261.43 |
| `target_data2b_feas1` | `serial` | 1 | 2 | 1.775748 | 0.0156 | 1.0208 | 265.86 |
| `target_data2b_feas1` | `dual` | 2 | 2 | 0.981818 | 0.0205 | 0.8226 | 278.24 |
| `target_data2b_feas1` | `intermediate` | 2 | 2 | 0.981818 | 0.0205 | 0.8226 | 278.24 |
| `target_data2b_feas1` | `auto` | 3 | 2 | 0.854212 | 0.0427 | 0.6522 | 283.77 |
| `target_data2c_mvidx1` | `serial` | 1 | 2 | 2.171187 | 0.0075 | 1.0179 | 295.64 |
| `target_data2c_mvidx1` | `dual` | 2 | 2 | 2.290016 | 0.0096 | 0.4996 | 295.88 |
| `target_data2c_mvidx1` | `intermediate` | 2 | 2 | 2.290016 | 0.0096 | 0.4996 | 295.88 |
| `target_data2c_mvidx1` | `auto` | 3 | 2 | 2.396963 | 0.0093 | 0.3338 | 297.13 |
| `target_data2c_mvsel1_kernel` | `serial` | 1 | 2 | 3.030540 | 0.0089 | 1.0122 | 263.19 |
| `target_data2c_mvsel1_kernel` | `dual` | 1 | 2 | 3.001256 | 0.0717 | 1.0148 | 263.20 |
| `target_data2c_mvsel1_kernel` | `intermediate` | 1 | 2 | 3.001256 | 0.0717 | 1.0148 | 263.20 |
| `target_data2c_mvsel1_kernel` | `auto` | 1 | 2 | 2.834313 | 0.0071 | 1.0155 | 263.13 |
| `replay_unified_extxyz_ingest` | `serial` | 1 | 2 | 7.763371 | 0.0055 | 1.0128 | 258.30 |
| `replay_unified_extxyz_ingest` | `dual` | 1 | 2 | 7.671910 | 0.0002 | 1.0156 | 258.45 |
| `replay_unified_extxyz_ingest` | `intermediate` | 1 | 2 | 7.671910 | 0.0002 | 1.0156 | 258.45 |
| `replay_unified_extxyz_ingest` | `auto` | 1 | 2 | 8.349185 | 0.0190 | 1.0181 | 258.79 |

## Unavailable on this host

- FOUNDATION-AUDIT1 model-inference and residual-reduction baseline (MACE runtime unavailable on cloud host)
- EVAL2 checkpoint-inference/statistics baseline (MACE runtime unavailable on cloud host)

## Limitations

- Cloud CPU authority is cgroup-constrained; automatic workers use mdstats' detected CPU budget.
- TARGET-DATA2B family extraction/target XML parsing is performed once outside timed radius trials; replay parsing is timed directly.
- FEAS1/MVIDX1/MVSEL1 scaling workloads are deterministic synthetic authorities so algorithmic changes can be compared without model inference noise.
- No GPU performance authority is asserted by PERFBASE1.
