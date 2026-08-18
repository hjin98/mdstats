# LD8-S3 hybrid tiled executor benchmark

- Total elapsed: `22.248 s`

| Field | Grid | Tiles (D/F) | Atlas | S3 realize | LD7 realize | Speedup | Peak RSS | Rel. L1 gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Al density | 1037x1037x1037 | 119 (12/107) | 14.345 s | 2.146 s | 56.022 s | 26.11x | 0.979 GiB | tests |

Scientific equivalence is enforced by the focused S2 comparison suite; the production benchmark measures execution and support counts without repeating the full LD7 field.
