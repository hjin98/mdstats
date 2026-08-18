# mdstats 0.20.216a0 - TRAIN2 FP32 repeatability diagnostic hotfix

## Scope

This release adds diagnostic measurement only. It does not change any e3nn/CuEq parity tolerance or scientific convergence criterion.

## Diagnostic

- Run 10 repeated e3nn and 10 repeated pure-CuEq TRAIN2 evaluations for FP32 phase-separated CuEq doctor checks.
- Report paired `Emax`, `Fmax`, `Frmse`, force p99/p99.9, force-component count above `1e-5`, `Smax`, `Dmax`, and selection identity for every repetition.
- Report aggregate min/median/p90/max for e3nn-self `Fmax`, CuEq-self `Fmax`, cross-backend `Fmax`, `Frmse`, p99, and p99.9.
- Print PyTorch/cuDNN/CUBLAS determinism state.
- Persist the content-addressed non-authorizing diagnostic record in campaign state.

## Unchanged authority

TRAIN2 FP32 remains `rtol=1e-5, atol=1e-5`. Generic source/DATA6 FP32 remains `rtol=1e-5, atol=1e-6`; FP64 remains `rtol=1e-10, atol=1e-12`. FINAL-GPU1 HF2 is held archival until the workstation repeatability values are reviewed.
