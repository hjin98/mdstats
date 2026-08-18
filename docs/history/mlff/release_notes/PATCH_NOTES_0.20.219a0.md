# mdstats 0.20.219a0 - CUEQ-REPEAT1-PARITY1

This release freezes the permanent TRAIN2 FP32 backend-equivalence policy from the MPA-0 DIAG3 evidence.

- Stable energy/stress/descriptor channels use the tight FP32 `rtol=1e-5`, `atol=1e-6` authority.
- Forces use one discarded warm-up and ten post-warm-up outputs per backend.
- Authorization compares 45 e3nn-self, 45 CuEq-self, and 100 e3nn/CuEq all-pairs statistics.
- For `Frmse`, `Fp99`, and `Fp99.9`, the p99 cross statistic must be no more than 1.25 times the larger p99 same-backend envelope.
- Cross `Fmax` is a catastrophic-tail guard: it must be below both 1.5 times the observed same-backend maximum and `1e-4 eV/A`.
- All self/cross selection fingerprints must remain identical and all values must remain finite.
- The deterministic-control subprocess is retained as an optional diagnostic but is not part of routine production qualification.

The policy is a numerical backend-equivalence test. It does not change scientific convergence, model-quality, DATA8, or deployment tolerances.
