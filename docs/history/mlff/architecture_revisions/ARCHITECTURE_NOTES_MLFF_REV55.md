# MLFF architecture revision 55

**Release:** `mdstats 0.20.188a0`  
**Gate:** CUEQ-DEP1 implementation  
**Date:** 2026-08-15

Revision 55 implements the accelerator-runtime freeze needed by the final consolidated GPU campaign without performing intermediate GPU qualification.

## Decisions

- CUEQ-DEP1 has a dedicated `CueqDep1RuntimeRecord.v1`; it is no longer represented only by version strings in the older generalized MACE runtime probe.
- Phase-1 source inference remains e3nn and training remains pure CuEq. OpenEquivariance is recorded but optional for this gate.
- CuEq capability requires **core + Torch frontend + CUDA ops**. The older final-GPU preflight omitted the ops layer; that gap is closed.
- CUDA-major ops discovery accepts cu13, cu12, cu11, and generic distributions while binding the exact installed provider into evidence.
- Required Python distributions are content-addressed using installed `METADATA`/`RECORD`/`WHEEL` evidence plus the imported module-root hash.
- CUDA device, driver/toolkit, cuDNN, deterministic-algorithm, TF32, matmul, and selected environment settings are frozen as runtime provenance.
- Absence/mismatch produces a durable negative record and never causes backend fallback.

## Qualification state

The implementation and fail-closed control plane are CPU-qualified. The development host has MACE 0.3.16 and e3nn 0.4.4 but CPU-only PyTorch and no CuEq core/Torch/ops packages, so CUEQ-DEP1 correctly remains unqualified scientifically/runtime-wise until FINAL-GPU1.

## Next gate

CUEQ-PHASE1 implementation is next. Its actual paired CuEq training qualification remains deferred to the single FINAL-GPU1 workstation run.
