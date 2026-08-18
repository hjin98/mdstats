# LD8-S2 canonical direct-realization benchmark

This bounded benchmark validates the S2 migration oracle. It is not a
claim that S2 replaces the production LD7 executor before LD8-S3.

| Source nodes | Stencil offsets | Exact pairs | Candidate pairs | Target nodes | S2 time | LD1-A time | S2/LD1-A | Relative L1 | Packed field |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 8,409 | 538,176 | 676,756 | 407,999 | 0.502 s | 0.328 s | 1.53x | 1.467e-18 | 3.22 MiB |
| 128 | 8,409 | 1,076,352 | 1,938,781 | 609,687 | 0.881 s | 0.442 s | 1.99x | 2.129e-16 | 4.76 MiB |
| 512 | 8,409 | 4,305,408 | 14,235,800 | 880,724 | 2.526 s | 0.801 s | 3.16x | 4.097e-17 | 6.83 MiB |

S2 is exact and bounded, but the current NumPy target-owned oracle is
slower than LD1-A on these small-to-medium cases. This is expected and
supports retaining LD7 for production until the LD8-S3 hybrid executor
passes its crossover and full-field performance gates.
