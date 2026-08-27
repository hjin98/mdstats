# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

Current MLFF workplans:

- `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md` — controlling target-size correction: `fidelity_epochs` are exact screening boundaries only; production `n` is independent. This supersedes conflicting screen-horizon language in the older final-closure plan while its implementation/validation is in progress.
- `MLFF_EVALUATION_PIPELINE_RAM_LEASE_FIX_WORKPLAN.md` — staged-evaluation RAM admission/resource-authority repair for the one-outer-owner nested inference path. It is a prerequisite for uncached target-size evaluation paths affected by the PERF1 regression and does not reopen target-size scientific semantics.
- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry, including TARGET-SIZE-V5.

The completed TARGET-SIZE-V5 EVAL2 staged-execution/performance workplan is archived at `../archive/MLFF_TARGET_SIZE_EVAL2_STAGED_EXECUTION_OPT1_WORKPLAN.md`; accepted execution ownership and compatibility rules now live in the current architecture/specification documents.

The prior target-size Repair-1 chain and its final-closure plan are superseded for active closure by the exact-boundary rework and retained only as historical engineering context under `../archive/`:

- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW1_AMENDMENT.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW2_AMENDMENT.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md`

Those superseded plans do not independently impose additional active gates. Their still-valid architecture decisions and evidence remain reusable, but implementation must not reconstruct the older broad acceptance matrix unless current exact-boundary or assembled recovery evidence exposes a concrete product defect.

The target-size screen/production-horizon decoupling architecture workplan is archived at `../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md`. Its nonconflicting design remains reusable: screening and production are distinct roles, screen continuation is exact `n1 -> n2 -> n3`, and production is a fresh selected-size campaign. Its former treatment of `n3` as a screen horizon is superseded by the exact-boundary rework above.

The older flexible-fidelity Rework-3 chain was explicitly retired by user decision on 2026-08-25 and is retained in `../archive/` as historical engineering context:

- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md`

Archived Rework-3 review findings do not independently reopen work or impose standalone active gates. Full GPU and long real-data production qualification remain deferred to FINAL-GPU1.
