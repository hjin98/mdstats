# AUDIT-EVAL-PERF1 cloud CPU benchmark

Release: mdstats 0.20.233a0 / architecture revision 100  
Active qualification foundation: MACE-MPA-0 medium (`75428afe3a1d...fb493e38604fb638`)  
MACE-MH-1 compatibility: yes; no model inference path is changed or benchmarked here.

## Exactness

- EVAL2 target metric digest: `d9dd9db2c2d47e2d6f034e0b58f094c04c516d5a0dc4f0089d3f15762d434658` (identical to untouched 0.20.232a0).
- Paired-bootstrap comparison digest: `9664354fd2d871e67113ff5b9ef28118c9414a59f29a5fd4114acb729590397e` (identical to untouched 0.20.232a0).
- FOUNDATION-AUDIT1 digest: `39b8b207c741798f5a8555b41ceb0c746948935612d84d45961ba87b0e8c94e5` (identical to untouched 0.20.232a0).
- Foundation model-provider call counts remain 44 descriptor / 44 prediction calls; AUDIT-EVAL-PERF1 performs no extra inference.

## Same-host medians

| CPU reduction | 0.20.232a0 | 0.20.233a0 | speedup |
|---|---:|---:|---:|
| EVAL2 target metrics, 4,096 configurations / 294,912 atoms | 0.862081 s | 0.449215 s | 1.92x |
| Paired bootstrap, 768 blocks / 2,000 replicates | 0.051167 s | 0.015223 s | 3.36x |
| FOUNDATION-AUDIT1 no-inference fixture | 0.058029 s | 0.054530 s | 1.06x |

The Foundation Audit fixture is intentionally described as a modest gain: prediction-sidecar authentication and structural-conditioned evidence remain necessary work. EVAL2 benefits much more because repeated checkpoint reductions now reuse immutable indexing metadata and the bootstrap no longer pays one Python iteration per replicate.

Timing is execution evidence only. Persisted audit/metric/bootstrap records remain scientific authority.
