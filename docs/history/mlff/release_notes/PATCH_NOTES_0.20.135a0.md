# mdstats 0.20.135a0 patch notes

## MLCV-SELECT1

This release implements the fifth conventional-CV correction gate. Each completed run now full-evaluates every retained RANK1 checkpoint on its proper complete checkpoint-selection target domain and complete TRUE_DFT replay domain. Full component-wise acceptance gates are applied before the best surviving full-score checkpoint is frozen as that run's representative.

Fold selection uses `V_i_full` only; the outer fold remains untouched until MLCV-AGG1. Final-development selection uses `D_full`. New MLCV campaigns stop after SELECT1 and do not use the historical campaign-wide ADAPT-EVAL1 champion pool.

## STOP1 factors

`target_stop_fraction` and `replay_stop_multiplier` are configurable TOML values again. Defaults remain 0.80 and 1.20. The resolved lightweight stop errors are always derived from `T_full_max` and the weight-derived `R_full_max`; the factors do not modify the authoritative full-validation thresholds.
