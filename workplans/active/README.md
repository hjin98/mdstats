# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

Current MLFF workplans:

- `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md` — controlling target-size correction: `fidelity_epochs` are exact screening boundaries only; production `n` is independent. This supersedes conflicting screen-horizon language in the older final-closure plan while its implementation/validation is in progress.
- `MLFF_TARGET_SIZE_EVAL2_STAGED_EXECUTION_OPT1_WORKPLAN.md` — execution/performance companion for TARGET-SIZE-V5 exact-boundary EVAL2: migrate the private serial endpoint loop onto the existing OPT-EVAL4 staged scheduler, restore hierarchical progress/heartbeat, consolidate shared target data, and evaluate deeper provider/calibration/GPU concurrency optimizations only behind representative evidence gates. It is subordinate to the exact-boundary scientific workplan above and does not change target-size ranking semantics.
- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry, including TARGET-SIZE-V5.
The prior target-size repair chain and its final-closure plan are superseded for active closure by the exact-boundary rework and retained only as historical engineering context:

- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW1_AMENDMENT.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW2_AMENDMENT.md`

The superseded final-closure plan is archived at `../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md`.

Those superseded plans do not independently impose additional active gates. Their still-valid architecture decisions and evidence remain reusable, but implementation must not reconstruct the older broad acceptance matrix unless the final assembled recovery test produces evidence that a retired surface is actually broken.

The target-size screen/production-horizon decoupling architecture workplan is archived at `../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md`. Its nonconflicting design remains reusable: screening and production are distinct roles, screen continuation is exact `n1 -> n2 -> n3`, and production is a fresh selected-size campaign. Its former treatment of `n3` as a screen horizon is superseded by the exact-boundary rework above.

The older flexible-fidelity Rework-3 chain was explicitly retired by user decision on 2026-08-25 and is retained in `../archive/` as historical engineering context:

- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md`

Archived Rework-3 review findings do not independently reopen work or impose standalone active gates. Full GPU and long real-data production qualification remain deferred to FINAL-GPU1.
