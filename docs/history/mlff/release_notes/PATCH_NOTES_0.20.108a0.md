# mdstats 0.20.108a0 patch notes

This release implements MLFF staged-precision gate **PREC1**. It freezes configuration,
schedule resolution, and protocol identity; it does **not** yet implement the live
FP32->FP64 transition (PREC2) or complete profile runtime activation (PREC3).

## Added

- `mdstats.training_data.precision_schedule` with canonical `single`, `double`, and
  `refine` profiles, generalized multi-stage policies, deterministic epoch/update
  resolution, refinement floors, and authenticated resolved schedules.
- `mdstats-mlff-campaign init --precision {single,double,refine}`. Plain `init` is
  exactly `--precision single`.
- Generated TOML exposes the requested profile and every precision stage explicitly.
  Canonical `refine` is 80% FP32 then 20% FP64, LR scale 1.0 then 0.5, with a three
  FP64-epoch and 15,000-gradient-update refinement floor.
- DATA8 resolves precision stages after effective target/replay loader exposure is
  known and binds resolved epoch/update boundaries into `TrainingProtocolIdentity`.

## Compatibility and fail-closed behavior

- Existing configs without `[training.precision]` remain schedule-free and preserve
  the previous v4 optimizer/v2 protocol serialization and digests.
- Historical FP32-body/critical-FP64 behavior remains representable as a legacy/custom
  one-stage policy; it is not silently relabeled canonical `single`.
- The critical-precision policy schema can now represent canonical native FP32 critical
  operations for `single` without altering legacy FP64 policy bytes/digests; actual
  canonical-single execution remains fail-closed until PREC3.
- Until PREC2/PREC3 are implemented, preflight refuses explicit multi-stage schedules
  and canonical-single critical-FP32 execution instead of silently running the wrong
  arithmetic.

## Architecture

MLFF dependency-graph schema remains 26 and architecture revision advances to 27.
`PREC1` is complete; `PREC2` is the next implementation gate.
