# MLFF architecture revision 28 - ADAPT-RANK1 implementation

This release implements `ADAPT-RANK1` on top of the common online monitors and adaptive training
stop evidence established by ADAPT-MON1/ADAPT-STOP1.

Implemented contract:

- no new MACE inference and no checkpoint-model deserialization during lightweight ranking;
- hard target/replay candidate boundaries are reapplied before weighted scoring;
- replay-enabled score is `(w_T*T_mon + w_R*R_mon)/(w_T + w_R)`; target-only score is `T_mon`;
- default 1:1 target:replay weighting is the simple arithmetic mean;
- exactly one run-local champion is selected when at least one admissible epoch exists;
- deterministic ordering uses weighted score, target RMSE, replay RMSE, earlier epoch, then
  checkpoint SHA-256;
- mathematically equal scores are canonicalized only at a sub-femtoscale comparison tolerance so
  binary FP64 representation noise cannot bypass the documented tie breakers;
- runs with no admissible epoch persist an explicit no-champion outcome;
- `lightweight_run_champion.json` binds run, protocol, STOP1 policy/state, checkpoint catalog, and
  common ADAPT-MON1 monitor identities;
- reconciliation regenerates the same artifact from persisted evidence without opening model
  checkpoints and fails closed on mismatch.

The canonical contract is documented in
`docs/history/mlff/retired_specs/mlff_lightweight_ranking_spec.{md,pdf}` and the MLFF architecture manual.
ADAPT-EVAL1 remains the next gate; EVAL-MF is still runtime-authoritative for campaign-wide
checkpoint evaluation in 0.20.125a0.
