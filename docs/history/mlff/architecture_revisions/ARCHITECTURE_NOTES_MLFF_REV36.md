# MLFF Architecture Revision 36 - MLCV-AGG1 implementation

`mdstats 0.20.136a0` implements MLCV-AGG1, the sixth gate of the conventional cross-validation redesign accepted in revision 32.

A fold representative is now frozen completely before the rotating outer fold becomes visible. AGG1 evaluates only that exact representative on the complete `C_i` target domain. Outer-fold evidence can pass or fail the fold, but it has no authority to select another epoch. Replay evidence is not rotated: the fold report reuses the representative's complete TRUE_DFT `R_full` result from SELECT1.

Each configured seed publishes separate target/replay/combined cross-validation summaries with mean, sample standard deviation, minimum, maximum, range, and worst fold. Every configured fold must produce a representative and pass the outer target ceiling. Cross-fold dispersion remains diagnostic-only until an empirical hard-consistency threshold is justified. All fold representatives are permanently production-ineligible.

MLCV-FINAL1 remains the next gate. It will compare only qualified final-development representatives across seeds and create the single-best and committee selection products; no such production selection is created by AGG1.
