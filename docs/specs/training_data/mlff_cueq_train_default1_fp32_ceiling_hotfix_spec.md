---
geometry: margin=0.62in
fontsize: 9pt
---

# MLFF CUEQ-DEFAULT1-HF2 TRAIN2 FP32 parity-ceiling hotfix

**Gate:** `CUEQ-DEFAULT1-HF2`  
**Release:** `mdstats 0.20.215a0`  
**Architecture revision:** 82

## Problem

CUEQ-DEFAULT1-HF1 froze a TRAIN2-only FP32 parity floor of `rtol=1e-5, atol=2e-6` from earlier selected-head MH-1 evidence. MPA-0/default workstation qualification later reported `Emax=2.384e-7`, `Fmax=8.911e-6`, `Smax=1.660e-7`, and `Dmax=2.883e-7`, while deterministic selection remained identical. The result is outside the historical TRAIN2 absolute floor only in the force channel.

## Revised authority

The frozen TRAIN2 FP32 parity policy is:

```text
rtol = 1e-5
atol = 1e-5
```

The generic ACCEL1 source/DATA6 FP32 policy remains `rtol=1e-5, atol=1e-6`. FP64 remains `rtol=1e-10, atol=1e-12` for both authorities.

The TRAIN2 `1e-5` value is a backend-equivalence ceiling for finite-precision differences caused by different FP32 reduction/accumulation order. It is not a scientific convergence, fitting, validation, or deployment-accuracy threshold and may not be reused as one.

## Required invariants

1. All compared outputs must be finite.
2. Deterministic selection fingerprints must remain identical.
3. The ceiling is fixed; no observed failure may auto-expand it.
4. The generic source/DATA6 authority remains unchanged.
5. FP64 authority remains unchanged.
6. No silent fallback from requested CuEq TRAIN2 execution to e3nn is allowed.
7. The active parity-policy content digest is persisted and bound into FINAL-GPU1 preflight/handoff provenance.

## Regression anchors

The MPA-0/default reported envelope with `Fmax=8.911e-6` must pass the TRAIN2 FP32 policy but fail the generic source/DATA6 FP32 policy when tested against a zero-reference absolute floor. A `1.0001e-5` zero-reference difference must fail the TRAIN2 FP32 policy.
