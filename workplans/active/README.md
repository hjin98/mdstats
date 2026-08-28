# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

Current MLFF workplans:

- `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` — controlling reviewed architecture reset for target-size population/evaluation semantics: global correlation/equivalence-safe training-priority allocation before CV construction, rich training selection inside the reserved pool, one frozen residual per-domain M1/M2/M3 target-size evaluation ladder, configurable exponent-based target ladders, configured-ceiling semantics, M3 reuse for final-development checkpoint selection after size freeze, and destructive retirement of incompatible current-generation state/legacy complement/fixed-universe paths. It supersedes conflicting target-size population/evaluation/compatibility statements in older plans while preserving their nonconflicting exact-boundary and fresh-production doctrine.
- `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md` — controlling target-size correction for nonconflicting screening-continuation semantics: `fidelity_epochs` are exact screening boundaries only; production `n` is independent. Its former fixed-candidate-universe, old EVAL2-population, or TARGET-SIZE-V5 population-generation assumptions are superseded by the reviewed training-priority evaluation-ladder architecture reset above.
- `MLFF_EVALUATION_PIPELINE_RAM_LEASE_FIX_WORKPLAN.md` — staged-evaluation RAM admission/resource-authority repair for the one-outer-owner nested inference path. It is a prerequisite for uncached target-size evaluation paths affected by the PERF1 regression and does not reopen target-size scientific semantics.
- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry. Any TARGET-SIZE-V5 population-generation wording in that plan is historical/superseded by the active architecture reset; its nonconflicting lifecycle/provenance obligations remain current.

The completed TARGET-SIZE-V5 EVAL2 staged-execution/performance workplan is archived at `../archive/MLFF_TARGET_SIZE_EVAL2_STAGED_EXECUTION_OPT1_WORKPLAN.md`; its accepted execution/resource ownership remains reusable, but its historical full-complement population and TARGET-SIZE-V5 generation semantics are superseded by the active architecture reset.

The prior target-size Repair-1 chain and its final-closure plan are superseded for active closure by the current target-size workplans and retained only as historical engineering context under `../archive/`:

- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW1_AMENDMENT.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW2_AMENDMENT.md`
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md`

Those superseded plans do not independently impose additional active gates. Their still-valid architecture decisions and evidence remain reusable, but implementation must not reconstruct superseded population, migration, or compatibility semantics.

The target-size screen/production-horizon decoupling architecture workplan is archived at `../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md`. Its nonconflicting design remains reusable: screening and production are distinct roles, screen continuation is exact `n1 -> n2 -> n3`, and production is a fresh selected-size campaign. Its former treatment of `n3` as a screen horizon and any fixed-population assumptions are not current authority.

The older flexible-fidelity Rework-3 chain was explicitly retired by user decision on 2026-08-25 and is retained in `../archive/` as historical engineering context:

- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md`

Archived Rework-3 review findings do not independently reopen work or impose standalone active gates. Full long real-data/GPU production qualification remains deferred to FINAL-GPU1; unavailable scientific sampling-policy qualification must be reported as deferred rather than passed.