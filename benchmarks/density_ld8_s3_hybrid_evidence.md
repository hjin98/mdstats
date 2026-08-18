# LD8-S3 hybrid executor evidence

Production scientific policy: `kernel_tail_tolerance=1e-8`; compute tile `32^3`.

## Full-trajectory fields

| Field | Grid | Source nodes | Direct / FFT tiles | Hybrid realization | LD7 baseline | Speedup | Repairs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Na density | 540x540x540 | 36,280 | 10 / 105 | 2.088 s | 41.934 s | 20.08x | 10 |
| Si density | 1038x1038x1038 | 54,680 | 14 / 94 | 2.015 s | 54.244 s | 26.91x | 1 |
| Al density | 1037x1037x1037 | 57,471 | 12 / 107 | 2.146 s | 56.022 s | 26.11x | 0 |

The full production oxygen run was not completed in this S3 validation session because repeated construction of the pre-existing S1 oxygen atlas showed unstable wall time in the shared execution environment. The prior exact S1 oxygen atlas remains validated, and the oxygen-heavy focused S3 fixture passed against S2. S4 must rerun all four channels before production migration.

## Focused crossover cases

| Case | Source nodes | Direct / FFT tiles | Hybrid | S2 | Speedup | Relative L1 |
|---|---:|---:|---:|---:|---:|---:|
| fragmented | 64 | 24 / 0 | 0.2356 s | 0.6611 s | 2.81x | 2.897e-18 |
| compact | 512 | 0 / 1 | 0.0281 s | 1.1345 s | 40.44x | 5.318e-16 |
| boundary_crossing | 128 | 18 / 0 | 0.1577 s | 0.7101 s | 4.50x | 4.316e-17 |
| oxygen_heavy | 2,047 | 0 / 27 | 0.6474 s | 8.9178 s | 13.78x | 5.095e-16 |
