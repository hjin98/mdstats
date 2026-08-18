# MVKERNEL1 cloud-CPU qualification benchmark

Release: `mdstats 0.20.230a0`  
Architecture revision: 97  
Active foundation checkpoint: MACE-MPA-0 medium (`75428afe...638`)  
Scientific scope: foundation-model independent; MACE-MH-1 remains supported.

## Scientific equivalence

- Representative MVSEL ordered-selection digest: `d147d85acd64dd386dcd9b64e1bd534001e1b1a9e1736522b2ffaddbb978b378`.
- 16,384-selection stress digest: `aaec42fb0c1df6a62ce2286ec5f5b8897bc089d6d31726da89a0461bcd75d608`.
- MVQUAL telemetry authority digest: `d51daef220edffd1f9a72676ee5835ed4f0db44d8818b78f3449defcba63894c`.
- Full MVQUAL plan digest: `ff8f64607a4835309889cb9b4c1e886959d9e47468a48df07676e0bf32295a80`.
- Optimized MVSEL state agrees with the retained scalar reference after every qualified rank.
- Optimized MVQUAL telemetry serializes byte-for-byte identically to the retained scalar reference.

## Same-host execution evidence

| Workload | 0.20.229a0 | 0.20.230a0 | Speedup |
|---|---:|---:|---:|
| MVSEL n=4096, k=2048, degree=24, 3 families (median of 5) | 1.404 s | 0.811 s | 1.73x |
| MVSEL n=24576, k=16384, degree=8, 2 families | 6.640 s | 5.591 s | 1.19x |
| MVQUAL telemetry n=16384, selected=8192, degree=16, 6 families (median of 5) | 0.578 s | 0.041 s | 14.05x |

Timing is execution evidence only. Exact state, serialized records, and scientific digests are the acceptance authority.

## Decision

MVKERNEL1 passes. Sequential rank authority and independent TARGET-DATA2B rescoring are unchanged. The next optimization gate is `REPAIR-PAR1`.
