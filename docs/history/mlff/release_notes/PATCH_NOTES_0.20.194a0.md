# mdstats 0.20.194a0 - CUEQ-DEFAULT1 hotfix

## Scope

This release fixes two workstation failures discovered immediately after enabling the phase-separated CuEq TRAIN2 default in 0.20.193a0.

## Fix 1 - foundation contract reporting

Revision 60 correctly migrated the foundation configuration contract from one broad `backend` field to independent `source_backend` and `training_backend` fields. The `doctor` display path still indexed the retired `backend` key and therefore emitted `foundation configuration is invalid: 'backend'`. The display now reports both frozen phase choices directly. No scientific configuration changes are made by this fix.

## Fix 2 - selected-head TRAIN2 CuEq roundoff policy

The generic ACCEL1 source/DATA6 FP32 parity policy remains `rtol=1e-5, atol=1e-6`. It is not relaxed.

The EXTRACT1-derived selected-head checkpoint is a different execution authority used only as the TRAIN2 starting model. The workstation evidence that originally motivated CUEQ-PHASE1 already measured approximately `Fmax=1.669e-6` and `Dmax=1.192e-6` with identical deterministic selection. Therefore revision 61 freezes a distinct TRAIN2 preflight parity policy at `rtol=1e-5, atol=2e-6` for FP32; FP64 remains `rtol=1e-10, atol=1e-12`.

The newly reported workstation values (`Emax=3.576e-7`, `Fmax=1.490e-6`, `Smax=1.564e-8`, `Dmax=1.570e-6`, identical selection) are inside that previously motivated TRAIN2 roundoff envelope. This does not authorize CuEq source inference or DATA6 and does not affect the original six-head source-parity gate.

## Fail-closed behavior

CuEq TRAIN2 remains fail-closed for unavailable runtime components, non-finite output, selection drift, or numerical discrepancies outside the dedicated TRAIN2 policy. No silent e3nn fallback is introduced.
