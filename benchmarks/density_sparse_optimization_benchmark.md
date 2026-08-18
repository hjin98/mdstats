# LD5 sparse density optimization benchmark

| Fixture | Samples | Active nodes | Kernel pairs | Reference median (s) | Optimized median (s) | Speedup | Rel. L1 error |
|---|---:|---:|---:|---:|---:|---:|---:|
| localized | 300 | 3846 | 199595 | 0.023557 | 0.017140 | 1.37x | 1.702e-16 |
| broad | 300 | 216044 | 2500685 | 0.201682 | 0.107609 | 1.87x | 0.000e+00 |

## Canonical-support cache

- Cold median: `0.006179 s`
- Warm median: `0.000040 s`
- Speedup: `156.24x`
- Retained array bytes: `156864`
- Cache byte limit: `268435456`

The timings are evidence for this runtime, not portable unit-test thresholds.
