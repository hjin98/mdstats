# LD9-V1 tiled contour stress evidence

**Package:** `mdstats 0.19.59a0`  
**Source:** saved full-resolution fields from the 1,500-frame four-species stress scene  
**Shell:** 50% HDR for each species  
**Render tile:** `32 x 32 x 32` logical cells

| Species | Crossing cells | Tiles / MC calls | Indexed faces | Indexed vertices | Time |
|---|---:|---:|---:|---:|---:|
| Na | 45,293 | 110 | 90,306 | 45,505 | 9.30 s |
| Si | 39,064 | 111 | 77,948 | 39,028 | 8.17 s |
| Al | 42,365 | 88 | 84,552 | 42,334 | 8.15 s |
| O | 156,809 | 385 | 312,668 | 157,536 | 29.80 s |

Aggregate: **283,531** crossing cells, **694** marching-cubes calls, **565,474** faces, **284,403** vertices, and **55.42 s**.

The call count is **408.5x** smaller than one call per crossing cell. The Na 50% complete mesh-preparation path is **2.33x** faster than the retained legacy cell-wise oracle.

This is an extraction-stage benchmark, not the final browser acceptance gate. V1 deliberately retains unsimplified indexed geometry; LD9-V2 must reduce it under scalar-field, distance, normal, topology, and seam fidelity constraints. Periodic component labeling and strict whole-mesh validation remain enabled and are now visible downstream costs.
