# LD6 multilevel research benchmark

Decision: **retain_single_level**

| Field | Backend | Regime | Active fraction | Stored fraction | Best single-level values | Best candidate | Worst incremental reduction | Worst L1 | Time (s) |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| atomic_localized | local_sparse | localized | 0.0136 | 0.1481 | 3136 | - | - | - | 0.099 |
| framework_vertices_separated | local_sparse | localized | 0.0321 | 0.4815 | 8192 | - | - | - | 0.166 |
| oxygen_clouds_overlapping | local_sparse | localized | 0.0300 | 0.1852 | 6400 | - | - | - | 0.136 |
| na_multimodal_hopping | local_sparse | localized | 0.0438 | 0.1481 | 9280 | - | - | - | 0.184 |
| framework_edges_projected | local_sparse | localized | 0.1009 | 0.7037 | 23360 | - | - | - | 0.414 |
| framework_paths_atomic | local_sparse | localized | 0.1148 | 0.7037 | 22016 | 4x / q=0.99 | 2.900x | 1.662e-03 | 0.464 |
| mobile_ion_broad | dense | broad | 1.0000 | 1.0000 | 110592 | 2x / q=0.90 | 1.090x | 2.745e-04 | 5.579 |

## Decision rationale

- No required number of insufficient single-level cases shows a phase-robust multilevel gain large enough to justify transfer and contouring complexity.
- Some optimistic coarse/fine surrogates pass numerical tolerances, but they do not establish a production need beyond the completed backend selector.
- True multilevel transfer, HDR integration, and crack-free coarse/fine meshing remain unimplemented and must not be inferred from this research profiler.

## Notes

- The coarse/fine candidate is an optimistic research surrogate, not a production field.
- Every dyadic coarse-grid phase is evaluated; all phases must pass scientific tolerances.
- Single-level alternatives include 4^3, 8^3, and 16^3 block shapes.
