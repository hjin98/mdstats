# LD8-S3 hybrid tiled executor benchmark

- Total elapsed: `21.523 s`

| Field | Grid | Tiles (D/F) | Atlas | S3 realize | LD7 realize | Speedup | Peak RSS | Rel. L1 gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Na density | 540x540x540 | 115 (10/105) | 13.093 s | 2.088 s | 41.934 s | 20.08x | 0.962 GiB | tests |

Scientific equivalence is enforced by the focused S2 comparison suite; the production benchmark measures execution and support counts without repeating the full LD7 field.
