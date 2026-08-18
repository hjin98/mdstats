---
title: "mdstats 0.20.184a0"
subtitle: "FINAL-GPU1 deferred qualification workflow"
date: "2026-08-15"
geometry: margin=0.72in
fontsize: 9pt
---

This release changes **qualification scheduling**, not target-size science. The supplied foundation checkpoints are present and match the locked MLFF identities, while all GPU-dependent qualification is deliberately postponed until the final release package can be tested once on the user's CUDA/CuEquivariance workstation.

## Foundation inputs

- MACE-MH-1 / `omat_pbe`: `ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde`.
- MACE-MPA-0-medium / `default`: `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`.
- Current real-model CPU/e3nn regression: 27 passed, one source-tree-only skip.

The model binaries remain external locked inputs rather than duplicated package payloads.

## FINAL-GPU1

`FINAL-GPU1` separates implementation state from accelerator qualification state. During intermediate development, CPU/reference exactness, serialization, restart, and structural performance qualification continue normally. CUDA/CuEq results remain `pending` and cannot authorize a scientific default or performance claim.

The final workstation wave consolidates:

1. PREC3 real CuEq activation;
2. MH1-ACCEL1 e3nn/CuEq numerical parity;
3. MH1-DATA6-1 descriptor/selection parity;
4. MH1-TRAIN1 bounded CuEq training realization;
5. MH1-CERT1 generated-default CuEq matrix;
6. SIZE-FIDELITY1 exhaustive calibration; and
7. PERF-P2R whole-funnel GPU/VRAM performance.

ML-IAP/LAMMPS run-0 parity is packaged beside this wave but remains a separate deployment capability because it also requires an ML-IAP-enabled `lmp` executable.

## Development progression

SIZE-FIDELITY1 remains a hard **final-release** scientific blocker, but it no longer blocks code development. PERF-P2R and PERF-P3 may proceed only if they support the full calibration grid rather than assuming the current provisional 3-epoch / 256-frame / 1-meV/A values.

The one-shot readiness entry point is:

```text
tools/run_mlff_final_gpu_qualification.py
```

On the current host it verifies both checkpoint identities, MACE 0.3.16, and e3nn 0.4.4, then correctly records CPU-only PyTorch and missing CuEquivariance as `deferred_not_executed`.

## Documentation

The canonical MLFF architecture advances to revision 51 and dependency-graph schema 33. The normative workflow specification is `docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md`.
## PERF-P2R CPU/control-plane implementation

PERF-P2R is implemented without consuming deferred GPU evidence. Campaign training stages are authorized by one parameterized planner covering coarse endpoints 3, 4, and 5. DATA8 fixed files use an authenticated content-addressed cache and DATA7/DATA8 preparation can share one frame-array index. Exact structure-epoch accounting proves that promoted candidates continue incrementally rather than repaying completed prefixes.

On the bounded deterministic DATA8 fixture, 15 cache-hit builds exactly reproduce the fresh scientific authority. Median preparation wall time falls from 79.696 ms to 17.333 ms (4.598x, 78.25% lower). This is CPU/control-plane evidence only. Whole-funnel MACE/GPU timing, VRAM/utilization, resumed endpoint parity, and SIZE-FIDELITY1 calibration remain FINAL-GPU1 work.

The normative execution specification is `docs/specs/training_data/mlff_perf_p2r_successive_fidelity_execution_spec.md`. PERF-P3 is now the next implementation gate.

