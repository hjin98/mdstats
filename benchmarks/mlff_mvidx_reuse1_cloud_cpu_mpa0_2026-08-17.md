# MVIDX-REUSE1 cloud CPU qualification

Release `0.20.228a0`, architecture revision 95. Active campaign provenance is the supplied MACE-MPA-0 medium checkpoint (`75428afe3a1d...`); the gate is foundation-generic and applies unchanged to MACE-MH-1.

The workload is the frozen PERFBASE1/NEIGHBOR1 synthetic authority: 6 required families, 49,152 witnesses, and 3,194,880 exact forward edges. All schedules reproduce MVIDX digest `e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c` exactly.

| realization | median wall time | speedup vs untouched 0.20.227a0 |
|---|---:|---:|
| untouched 0.20.227a0 cached MVIDX | 0.590 s | 1.00x |
| 0.20.228a0, 1 lane | 0.156 s | 3.78x |
| 0.20.228a0, 2 lanes | 0.118 s | 5.02x |
| 0.20.228a0, 3 lanes | 0.087 s | 6.79x |

The performance gain comes from vectorized CSR row validation plus PARCORE1 scheduling of independent required-family/obligation inversions. Timing is execution evidence only; exact sparse arrays and digest equality are scientific authority.

**Acceptance: PASS. Next gate: COVREF-PAR1.**
