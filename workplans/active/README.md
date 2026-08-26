# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

Current MLFF workplans:

- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry, including TARGET-SIZE-V5.
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md` — **active acceptance/local-repair plan** for the target-size screen/production decoupling implementation at reviewed head `5916adb71adc7818b2969904c9486dbf90c8ff40`. The architecture remains accepted; Repair-1 reopens only proxy-proof persistence/restart/migration/orchestration acceptance and any concrete local defect those real-owner tests expose. Gate-closing tests must use real TOML/config normalization, SQLite `CampaignStore`, target-size/DATA8 compatibility owners, campaign/runtime authorization, and normal close/reopen reconciliation; only expensive external numerical MACE work may be faked below those owners.
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW1_AMENDMENT.md` — **mandatory Repair-1 lifecycle/recovery amendment**. Current source still emits role-blind scheduler interruption/retry instructions telling an active `select-target-size` screen to rerun public `train` and advertises non-public `--restart_latest`, even though public TRAIN2 `train`/`evaluate` correctly reject nonterminal target-size state. The shared TRAIN2 scheduler must become semantic-role-aware at its operator/recovery boundary without creating a second scheduler; real interruption/reopen/resume tests must prove `select-target-size` remains the sole screen lifecycle owner and production `train` remains separate.

The target-size screen/production-horizon decoupling architecture workplan is archived at `../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md`. Its frozen current design remains authoritative: screen horizon is `n3`, production horizon is independent `n`, screen continuation is exact `n1 -> n2 -> n3`, and production is a fresh selected-size campaign. Repair-1 does not reopen those decisions.

The older flexible-fidelity Rework-3 chain was explicitly retired by user decision on 2026-08-25 and is retained in `../archive/` as historical engineering context:

- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md`

Archived Rework-3 review findings do not independently reopen work or impose standalone active gates. Full GPU and long real-data production qualification remain deferred to FINAL-GPU1.
