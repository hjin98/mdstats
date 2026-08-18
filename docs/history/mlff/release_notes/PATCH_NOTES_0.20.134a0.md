# mdstats 0.20.134a0 patch notes

## MLCV-RANK1

This release closes the fourth conventional-CV correction gate. Each adaptive training run now ranks every checkpoint that has complete finite lightweight target/replay metrics and retains at most five candidates in deterministic score order. Fewer-than-five runs retain exactly the available candidates; no candidates are duplicated. Ranking launches no MACE inference, does not open checkpoint bytes, and cannot use an outer CV fold or full final-validation `D` as checkpoint-ranking authority.

The score remains

`S_light = (w_T*T_light + w_R*R_light)/(w_T+w_R)`.

The old `eligible_candidates` field name is retained for compatibility but, in new v2 ranking records, it contains the retained top-K rather than an unbounded historical eligible list. `rankable_checkpoint_count` records the number available before truncation and `candidate_limit` defaults to five. Rank-one checkpoint fields remain a temporary compatibility bridge for ADAPT-EVAL1 and are not a production-representative decision. MLCV-SELECT1 will consume all retained candidates.

## STOP1 derived-margin clarification

For new MLCV policy schema v2, the 80% and 120% factors are fixed policy constants. The adaptive stop boundaries are derived from the resolved full-validation criteria, not stored as independent 24/36 meV/A constants:

- `T_stop = 0.80 * T_full_max`;
- `R_full_max = (w_T / w_R) * T_full_max`;
- `R_stop = 1.20 * R_full_max`.

Thus the default 30 meV/A target criterion with 1:1 weights yields 24/36 meV/A, while a 40 meV/A target criterion with 2:1 target:replay weights yields a 32 meV/A target stop, an 80 meV/A replay full criterion, and a 96 meV/A replay-exhaustion stop.

Supplying a different `target_stop_fraction` or `replay_stop_multiplier` is rejected for new v2 policies; historical v1 stop policies retain their recorded values for exact restart compatibility. Historical v1 ranking evidence remains readable and is not silently rewritten.
