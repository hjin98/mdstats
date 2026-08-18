# MLFF architecture revision 33 - MLCV-RANK1 closure

Release: `mdstats 0.20.134a0`

This revision closes MLCV-RANK1, the fourth gate in the conventional-CV correction roadmap.

## STOP1 clarification frozen at this gate

For new MLCV policy schema v2, the 80% and 120% factors are fixed. The adaptive lightweight stop boundaries are derived from the resolved full-validation criteria; they are not independent absolute 24/36 meV/A constants:

- `T_stop = 0.80 * T_full_max`;
- `R_full_max = (w_T / w_R) * T_full_max`;
- `R_stop = 1.20 * R_full_max`.

Thus the default `T_full_max = 30 meV/A`, `w_T:w_R = 1:1` gives 24/36 meV/A, while changing either the target criterion or the score-weight geometry changes the stopping margins automatically. New v2 policies reject attempts to change the 0.80/1.20 factors themselves; legacy v1 evidence remains exact-restart compatible.

## MLCV-RANK1 implementation

Each independent training run now:

1. consumes only persisted lightweight STOP1 target/replay metrics and the frozen checkpoint catalog;
2. treats every checkpoint with complete finite nonnegative lightweight metrics as rankable, without applying the later full-validation 30 meV/A gates;
3. computes the target/replay weighted lightweight score;
4. sorts deterministically by weighted score, target RMSE, replay RMSE, epoch, then checkpoint SHA-256;
5. retains at most five candidates per run, or exactly the available number when fewer than five exist;
6. records both the retained top-K and the pre-truncation `rankable_checkpoint_count`; and
7. launches no MACE inference and opens no checkpoint bytes.

The existing rank-one fields remain temporarily populated only so the historical ADAPT-EVAL1 consumer can continue to execute until MLCV-SELECT1 replaces it. They are not a fold representative, final representative, or production winner under the MLCV authority.

Historical lightweight-run-champion schema v1 remains readable and is not silently rewritten. New ranking records use schema v2.

## Qualification

Focused STOP1/RANK1/integration suite: 85 passed, 3 legitimate optional/external-data skips.

Segmented broad dependency-independent MLFF suite, excluding only the known missing historical DATA9A9A restart-smoke fixture tests: 724 passed, 32 legitimate optional/external-data skips. Four other tests in the DATA9A9A specification file pass; the one fixture-dependent smoke assertion remains deselected because `release/mlff_data9a9a_real_mpa0_restart_smoke.json` is absent from the supplied source archive.

Packaged-tree STOP1/RANK1/specification verification: 22 passed, 0 failed.

Next gate: MLCV-SELECT1.
