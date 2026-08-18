# mdstats 0.20.133a0 patch notes

## MLCV-STOP1

This release implements the third conventional-CV correction gate, `MLCV-STOP1`.

- The default 24 meV/A target-success and 36 meV/A replay-exhaustion values at 1:1 target:replay weighting are now lightweight **training-control** signals only.
- Lightweight checkpoints are no longer rejected merely because their target or replay monitor RMSE crosses the authoritative 30 meV/A full-validation reference. Every checkpoint with complete finite lightweight target/replay metrics remains rankable for the later `MLCV-RANK1` gate.
- New campaigns require three completed epochs before either adaptive margin can terminate training. The independent hard 30-epoch ceiling remains in force.
- Foundation replay feasibility is purchased once from complete independent TRUE_DFT `R_full` before epoch 0, persisted with the replay artifact SHA-256, removed before the ordinary epoch loop, and reused/authenticated on exact restart.
- Adaptive stop policy/state serialization advances to v2. Historical v1 policies retain their original digest and old stopping/30-by-30 lightweight semantics rather than being silently reinterpreted.
- The campaign default remains three optimizer seeds, each with three CV folds plus one full-development final run (12 multi-head jobs total).

`MLCV-RANK1`, `MLCV-SELECT1`, CV aggregation, final-only production competition, and committee export remain later gates and are intentionally not implemented here.
