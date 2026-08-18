# LD8-S3 hybrid microbenchmark

| Case | Source nodes | Target nodes | Tiles D/F | Hybrid | S2 | Speedup | Relative L1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| fragmented | 64 | 398,664 | 24/0 | 0.236 s | 0.661 s | 2.81x | 2.897e-18 |
| compact | 512 | 23,032 | 0/1 | 0.028 s | 1.134 s | 40.44x | 5.318e-16 |
| boundary_crossing | 128 | 217,285 | 18/0 | 0.158 s | 0.710 s | 4.50x | 4.316e-17 |
| oxygen_heavy | 2,047 | 884,736 | 0/27 | 0.647 s | 8.918 s | 13.78x | 5.095e-16 |

All cases use the same finite normalized Gaussian stencil and exact support atlas.
