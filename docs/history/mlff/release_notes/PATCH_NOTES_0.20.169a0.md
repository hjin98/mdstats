# mdstats 0.20.169a0 patch notes

## Gate

`TRAIN2A` - replay becomes a hard retention constraint rather than a selection reward.

## Implemented

- Added four orthogonal immutable TRAIN2/EVAL2 policy authorities:
  - `TrainingBudgetPolicy`
  - `LearningRateSchedulePolicy`
  - `CheckpointAdmissibilityPolicy`
  - `CheckpointSelectionPolicy`
- Added v6 training-protocol and production-materialization identities for the complete TRAIN2 policy family.
- Preserved historical adaptive-stop protocol/materialization schemas and digest semantics; absence of `policy_generation` remains historical.
- Made foundation-relative TRUE_DFT replay degradation a hard admissibility gate with zero positive ranking or tie-break credit after admissibility.
- Made the target-only selection schema reject replay observables and use stable candidate identity as the final exact tie-break.
- New `init` output selects `policy_generation = "train2"` and `checkpoint_strategy = "train2_target_first"`, freezes the deterministic LR-policy parameters, and omits historical early-stop/replay-score controls.
- Mixed historical/new configuration controls fail closed rather than being silently reinterpreted; the old `maximum_replay_degradation_fraction` control is not emitted for TRAIN2 and is rejected when explicitly mixed into a new-policy config.
- TRAIN2 `train`, `evaluate`, and `verify` deliberately fail closed until TRAIN2B, EVAL2, SELECT2, and later physical-verification gates own those runtime paths.

## Intentionally deferred

- Actual fixed-budget training and per-optimizer-update LR stepping (`TRAIN2B`).
- Target-first full checkpoint-trajectory evaluation and paired-bootstrap ordering (`EVAL2`).
- Deployment/PES/relaxation/short-dynamics qualification and final physics-qualified selection (`DEPLOY-VERIFY1`, `PES-VERIFY1`, `RELAX-VERIFY1`, `DYN-VERIFY2`, `SELECT2`).

## Qualification

- 233 passed, 1 expected skip in the combined TRAIN2A + TARGET-DATA2A-E + FOUNDATION-AUDIT1 + campaign/materialization/historical-regression suite.
- The expected skip is the existing integration test requiring an external real LTA training root.
- Python compileall passed.
- Canonical architecture PDF regenerated at 126 pages; render comparison changed 17 expected TOC/roadmap/TRAIN2/EVAL2/SELECT2 pages and inspected pages 117, 118, 120, 122, and 123 render without clipping or broken glyphs.
- The separate historical DATA0 documentation suite remains 7 passed / 1 failed because one old assertion still hard-codes `0.20.140a0`; TRAIN2A specification tests pass.
