# LD8-S1 exact support-atlas benchmark

- Schema: `mdstats.density-ld8-s1-support-atlas-benchmark.v1`
- Kernel tail tolerance: `1.0e-08`
- Total benchmark time: `138.680 s`

| Field | Grid | Source nodes | Source blocks | Target blocks | Target nodes | Atlas time | Pair/shift reduction | LD7 count match |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Na density | 540x540x540 | 36,280 | 280 | 1,322 | 1,728,706 | 13.388 s | 129.6x | yes |
| Si density | 1038x1038x1038 | 54,680 | 280 | 1,381 | 1,833,591 | 13.301 s | 195.3x | yes |
| Al density | 1037x1037x1037 | 57,471 | 308 | 1,432 | 1,952,525 | 15.195 s | 186.6x | yes |
| O density | 646x646x646 | 187,821 | 1,132 | 5,625 | 7,274,190 | 55.158 s | 165.9x | yes |

The reduction ratio compares the complete fine interaction count
`occupied CIC nodes x stencil offsets` with the exact S1 count
`occupied source blocks x stencil offsets`. It is an operation-count
reference, not a claim of equal cost per operation.
