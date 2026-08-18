# CUEQ-REPEAT1-DIAG: TRAIN2 FP32 Repeatability Diagnostic Hotfix

**Release:** `mdstats 0.20.216a0`  
**Architecture:** revision 83  
**Dependency graph:** schema 65

## Purpose

Measure whether the observed TRAIN2 FP32 force-tail variation is intrinsic same-backend GPU nondeterminism or a stable e3nn-versus-CuEq offset. This gate is diagnostic only and does not authorize a new tolerance.

## Execution

For phase-separated TRAIN2 `training_backend = "cueq"` with FP32 and available CuEq, `doctor` performs 10 e3nn and 10 pure-CuEq evaluations over the same deterministic qualification structures using the exact selected training checkpoint/head.

For each paired repetition it records `Emax`, energy RMSE, `Fmax`, force RMSE, force p99, force p99.9, count of force components with absolute delta above `1e-5`, `Smax`, stress RMSE, `Dmax`, descriptor RMSE, and selection identity. Runs 2-10 are separately compared with run 1 for e3nn-self and CuEq-self force `Fmax`/RMSE.

## Printed statistics

Doctor prints each paired cross-backend repetition and aggregate min/median/p90/max summaries for:

- e3nn-self `Fmax`;
- CuEq-self `Fmax`;
- paired cross-backend `Fmax`;
- paired force RMSE;
- paired force p99 and p99.9; and
- force-component counts above `1e-5`.

It also prints the observed PyTorch deterministic-algorithm flag, deterministic debug mode, cuDNN deterministic flag, and `CUBLAS_WORKSPACE_CONFIG`.

## Authority

The diagnostic schema is `mdstats.training-acceleration-repeatability-diagnostic.v1`. It is persisted under `training_acceleration_repeatability_diagnostic`. The record is non-authorizing. The active TRAIN2 FP32 parity policy remains `rtol=1e-5, atol=1e-5` until the workstation diagnostic is reviewed.
