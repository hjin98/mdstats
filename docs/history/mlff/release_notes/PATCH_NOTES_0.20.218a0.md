# mdstats 0.20.218a0 - TRAIN2 repeatability DIAG3

CUEQ-REPEAT1-DIAG3 removes baseline bias from the temporary TRAIN2 FP32 repeatability diagnostic. Each e3nn and pure-CuEq calculator receives one discarded warm-up evaluation. Ten post-warm-up outputs are then retained per backend and compared offline using all pairs: 45 e3nn-self, 45 CuEq-self, and 100 cross-backend comparisons.

The diagnostic prints min/median/p90/p99/max force statistics, force-component exceedance counts, energy/stress/descriptor maxima, and selection identity. The isolated deterministic-control worker uses the same warm-up/all-pairs method.

This gate is measurement-only. The active TRAIN2 FP32 parity policy remains rtol=1e-5 and atol=1e-5. FINAL-GPU1 remains archival until DIAG3 workstation evidence is interpreted and a permanent noise-normalized criterion is frozen.
