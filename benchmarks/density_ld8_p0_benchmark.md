# LD8-P0 production-cutoff benchmark

- Scene: `/mnt/data/mdstats_0_19_53a0_TRAJECTORY4_scene.pkl`
- Tail tolerance: `1.0e-08`
- Existing LD7 execution enabled: **False**
- Total wall time: 38.953 s

| Field | Grid | CIC nodes | Stencil offsets | Estimated pairs | LD7 seconds |
|---|---:|---:|---:|---:|---:|
| Na density | 540x540x540 | 36,280 | 12,017 | 435,976,760 | not executed |
| Si density | 1038x1038x1038 | 54,680 | 12,017 | 657,089,560 | not executed |
| Al density | 1037x1037x1037 | 57,471 | 12,017 | 690,629,007 | not executed |
| O density | 646x646x646 | 187,821 | 12,017 | 2,257,044,957 | not executed |

The direct/FFT spike is a bounded evidence kernel only. It does not change the production backend or public API.
