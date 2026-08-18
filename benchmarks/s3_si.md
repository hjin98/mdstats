# LD8-S3 hybrid tiled executor benchmark

- Total elapsed: `23.235 s`

| Field | Grid | Tiles (D/F) | Atlas | S3 realize | LD7 realize | Speedup | Peak RSS | Rel. L1 gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Si density | 1038x1038x1038 | 108 (14/94) | 13.572 s | 2.015 s | 54.244 s | 26.91x | 0.953 GiB | tests |

Scientific equivalence is enforced by the focused S2 comparison suite; the production benchmark measures execution and support counts without repeating the full LD7 field.
