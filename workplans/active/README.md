# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

Current MLFF workplans:

- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry, including TARGET-SIZE-V5.
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md` — **controlling target-size design contract** for the genuine screening/production-horizon coupling defect. TARGET-SIZE-V5 screening targets its own successive-fidelity horizon `n3` (default `1 -> 3 -> 10`, horizon 10), while production `n` (default 30) is a separate fresh selected-size production campaign.

### Target-size precedence

For TARGET-SIZE-V5, read `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md` first. It is active and remains the implementation authority for the current design correction.

The older flexible-fidelity Rework-3 chain was explicitly retired by user decision on 2026-08-25 and is retained in `../archive/` as historical engineering context:

- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md`

Archived Rework-3 review findings do not independently reopen work or impose standalone active gates. Nonconflicting concerns that the active decoupling workplan explicitly incorporates remain applicable through that active workplan.

The active decoupling workplan is **not retired**. It addresses a genuine design issue discovered after the older Rework-3 effort and remains active until its own implementation/closeout lifecycle is complete or the user explicitly changes that decision.
