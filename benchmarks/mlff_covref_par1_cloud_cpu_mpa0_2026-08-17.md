# COVREF-PAR1 cloud CPU qualification benchmark

Release `0.20.229a0`, architecture revision 96. Active campaign provenance is the supplied MACE-MPA-0 medium checkpoint (`75428afe3a1d7d80…`); COVREF-PAR1 is foundation-generic and applies unchanged to MACE-MH-1.

## Scientific invariant

The PERFBASE1 supplied-family radius digest is exactly `823a2c0c2f8a012c84bee0fe27085535862b71ff48a75f31b6d96e52cd642e2d` for every qualified schedule and for the untouched 0.20.228a0 control. The 36,408-row weighted stress fixture is likewise byte-identical (`240d4eb275f217a09d2fc43b3b26ae136489f4351c52ede57b6a5bfc18f18480`).

## Supplied 4,100-frame / eight-family cache

| Schedule | Untouched 0.20.228a0 | COVREF-PAR1 0.20.229a0 |
|---|---:|---:|
| 1 lane | 0.509 s | 0.532 s |
| 2 lanes | 0.352 s | 0.334 s |
| 3 lanes | 0.279 s | **0.223 s** |

Three-lane paired speedup: **1.25×**. All three outer workers were observed busy. The one-lane queue path is intentionally reported even though it is slightly slower on this small fixture.

## 36,408-row nonuniform equal-unit/equal-frame stress family

Untouched 0.20.228a0 at three native cKDTree workers: **5.935 s**. COVREF-PAR1 at three outer lanes: **5.131 s**, a **1.16×** speedup. The adaptive scheduler emitted 361 cache-sized row tasks and used all three lanes.

Timing is execution evidence only. Exact arrays/digests are the gate authority.
