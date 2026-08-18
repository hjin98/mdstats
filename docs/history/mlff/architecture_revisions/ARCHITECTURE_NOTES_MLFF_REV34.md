# MLFF architecture revision 34 - configurable STOP1 factors and MLCV-SELECT1 closure

Release: `mdstats 0.20.135a0`

This revision closes MLCV-SELECT1, the fifth gate in the conventional-CV correction roadmap, and supersedes REV33's temporary statement that the 0.80/1.20 STOP1 factors were fixed.

## Configurable derived STOP1 margins

New MLCV adaptive-stop policy v2 keeps the same generated defaults but allows both dimensionless control factors to be configured in TOML:

- `target_stop_fraction = 0.80` by default, constrained to `0 < f_T < 1`;
- `replay_stop_multiplier = 1.20` by default, constrained to `f_R > 1`.

The runtime still derives the actual lightweight boundaries from the standard full criteria:

- `T_stop = f_T * T_full_max`;
- `R_full_max = (w_T / w_R) * T_full_max`;
- `R_stop = f_R * R_full_max`.

These factors do not alter the authoritative full-validation ceilings. They are protocol-frozen, restart-stable, and diagnostic plots show the realized factors rather than hard-coded 80%/120% labels.

## MLCV-SELECT1 implementation

For each completed training run, SELECT1 now:

1. consumes the entire retained RANK1 v2 shortlist (up to five checkpoints);
2. full-evaluates every retained checkpoint, with no early survivor shortcut;
3. uses complete nested `V_i_full` for fold target checkpoint selection and never queries the untouched outer CV fold;
4. uses complete held-out `D_full` for final-development checkpoint selection;
5. uses complete independent TRUE_DFT `R_full` replay validation for every run;
6. applies the full target ceiling, weight-derived replay ceiling, and configured energy/focus/stress/worst-condition gates before scoring;
7. ranks only surviving candidates by the full target/replay weighted score with deterministic tie-breaking; and
8. freezes exactly one immutable run representative or one explicit `no_representative` outcome.

New MLCV campaigns no longer enter the historical campaign-wide ADAPT-EVAL1 finalist queue. The `evaluate` command stops after run-local SELECT1 evidence and waits for MLCV-AGG1. Historical pre-MLCV adaptive campaigns retain their original ADAPT-EVAL1 authority.

## Scope boundary

SELECT1 does not evaluate fold representatives on outer folds, aggregate CV statistics, compare final seeds, export a production model/committee, perform physical verification, or activate locked test `E`. Those remain MLCV-AGG1/FINAL1/VERIFY1 responsibilities.

Next gate: MLCV-AGG1.
