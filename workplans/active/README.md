# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

Current MLFF workplans:

- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry, including TARGET-SIZE-V5.
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md` — **final target-size screen/production closure plan** at reviewed implementation head `892bed8ee2320d76e17491b7c71d29f46417adb2`. The only remaining active blocker is assembled real-owner interruption -> scheduler persistence -> close/reopen -> authentic automatic continuation for target-size screening and selected-size production, plus fail-closed cross-role restart. The private external numerical-child seam is the only permitted training fake. All previously cleared architecture/source obligations are retired from active gating unless this final assembled path exposes a concrete product defect.

The prior target-size repair chain is superseded for active closure by the final workplan above and retained only as historical engineering context:

- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW1_AMENDMENT.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW2_AMENDMENT.md`

Those superseded plans do not independently impose additional active gates. Their still-valid architecture decisions and evidence remain reusable, but implementation must not reconstruct the older broad acceptance matrix unless the final assembled recovery test produces evidence that a retired surface is actually broken.

The target-size screen/production-horizon decoupling architecture workplan is archived at `../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md`. Its frozen current design remains authoritative: screen horizon is `n3`, production horizon is independent `n`, screen continuation is exact `n1 -> n2 -> n3`, and production is a fresh selected-size campaign. The final closure plan does not reopen those decisions absent an explicit evidence-backed redesign trigger.

The older flexible-fidelity Rework-3 chain was explicitly retired by user decision on 2026-08-25 and is retained in `../archive/` as historical engineering context:

- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md`

Archived Rework-3 review findings do not independently reopen work or impose standalone active gates. Full GPU and long real-data production qualification remain deferred to FINAL-GPU1.
