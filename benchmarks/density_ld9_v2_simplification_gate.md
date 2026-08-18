# LD9-V2 full-resolution simplification gate

This evidence covers the four 50% HDR shells from the saved 1,500-frame stress scene. Each species was run in a fresh process with numerical-library threads limited to one, enforcing the intended extract–simplify–release memory boundary. It does not replace the LD9-V3 scene-wide 12-shell browser-budget gate.

| Species | Raw faces | Final faces | Reduction | Time (s) | Peak RSS (GiB) | Fidelity |
|---|---:|---:|---:|---:|---:|---|
| Na | 90,310 | 39,932 | 2.26× | 8.435 | 0.897 | pass |
| Si | 77,948 | 35,814 | 2.18× | 7.572 | 0.898 | pass |
| Al | 84,552 | 37,960 | 2.23× | 7.509 | 0.675 | pass |
| O | 312,672 | 112,930 | 2.77× | 26.923 | 0.905 | pass |

Total raw faces: **565,482**
Total final faces: **226,636**
Aggregate reduction: **2.50×**
Total species-isolated elapsed time: **50.440 s**
Maximum species peak RSS: **0.905 GiB**
All fidelity gates passed: **True**

The next stage must allocate and enforce one hard budget over all 12 shells after display replication.
