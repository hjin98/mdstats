# MLFF architecture revision 38 — MLCV-VERIFY1

`mdstats 0.20.138a0` closes MLCV-VERIFY1 of the conventional-CV correction roadmap.

The gate restricts bounded physical-verification fallback to qualified FINAL1 full-development representatives. Candidates are visited in authoritative FINAL1 order, fold models are never eligible, and the first physical passer is frozen permanently.

Locked post-freeze target test `E` is not materialized until that freeze exists. It is then evaluated target-only on the exact frozen FINAL1 target-head bytes. `E` has no fallback or selection authority: failure creates terminal campaign/review evidence under the current campaign identity.

Production publication is delayed until the frozen candidate passes both bounded physical verification and locked `E`. `models/production_best.model` is an atomic byte-identical copy of the verified FINAL1 committee artifact. The qualified seed committee remains separate for active learning.

New MLCV TOML exposes `fallback_to_next_qualified_final_seed = true`; historical ADAPT-VERIFY1 retains `fallback_to_next_full_evaluation_candidate`. MLCV verification policy identity freezes learned-model dtype, physical stability thresholds, the locked-E target threshold, and retained target safety-metric policy.

The remaining gate is MLCV-MIGRATE1.
