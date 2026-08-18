# MLFF Architecture Revision 61 - CUEQ-DEFAULT1-HF1

**Date:** 2026-08-16  
**Release:** `mdstats 0.20.194a0`  
**Dependency graph schema:** 43

Revision 61 hardens the revision-60 phase-separated default after first workstation execution.

1. `doctor` now consumes the v2 foundation contract using `source_backend` and `training_backend`; the retired aggregate `backend` key is never referenced.
2. Source inference, DATA6, pseudolabel generation, evaluation, and verification retain the generic ACCEL1 FP32 parity authority (`rtol=1e-5`, `atol=1e-6`).
3. The EXTRACT1-derived selected-head TRAIN2 starting checkpoint receives a separate, content-addressed FP32 parity authority (`rtol=1e-5`, `atol=2e-6`). FP64 remains unchanged (`rtol=1e-10`, `atol=1e-12`).
4. The 2e-6 TRAIN2 floor is not chosen from locked-test optimization. It is fixed from the earlier workstation selected-head evidence that motivated CUEQ-PHASE1 (`Fmax≈1.669e-6`, `Dmax≈1.192e-6`, identical selection).
5. The generic source/DATA6 tolerance is not relaxed, so the known multi-head MH-1 CuEq mismatch remains decisively rejected.
6. TRAIN2 CuEq remains fail-closed and never silently falls back to e3nn.
