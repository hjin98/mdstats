---
geometry: margin=0.58in
fontsize: 9pt
---

# MLFF CUEQ-DEFAULT1-HF1 Workstation Hotfix

**Gate:** `CUEQ-DEFAULT1-HF1`  
**Release:** `mdstats 0.20.194a0`  
**Architecture revision:** 61

This hotfix preserves the revision-60 split: source inference, DATA6, pseudolabels, evaluation, and verification use `e3nn`; TRAIN2 uses pure CuEq; exported checkpoints remain portable e3nn form (`only_cueq=false`).

## Foundation-contract correction

`FoundationConfigContract.v2` carries `source_backend` and `training_backend`. `doctor` now reports those exact fields and never indexes the retired aggregate `backend` field.

## Numerical authority

The generic ACCEL1 FP32 source/DATA6 parity policy remains unchanged at `rtol=1e-5, atol=1e-6`.

The EXTRACT1-derived selected-head TRAIN2 starting model uses a separate FP32 preflight policy: `rtol=1e-5, atol=2e-6`. FP64 remains `rtol=1e-10, atol=1e-12` for both authorities.

The TRAIN2 floor is frozen from the earlier selected-head workstation experiment that motivated CUEQ-PHASE1 (`Fmax` about `1.669e-6`, `Dmax` about `1.192e-6`, identical deterministic selection). It is not derived from locked-test tuning and does not change source/DATA6 acceptance.

## Workstation result disposition

The reported values `Emax=3.576e-7`, `Fmax=1.490e-6`, `Smax=1.564e-8`, `Dmax=1.570e-6`, with `selection_identical=True`, are inside the frozen TRAIN2 FP32 policy. They are intentionally not used to alter the generic source/DATA6 policy.

## Fail-closed requirements

TRAIN2 CuEq remains non-authorizing if the CuEq/CUDA runtime freeze fails, the selected-head checkpoint identity is invalid, any energy/force/stress/descriptor output is non-finite, deterministic selection fingerprints differ, or numerical differences exceed the dedicated TRAIN2 policy. No silent e3nn fallback is allowed.
