# mdstats 0.20.130a0 patch notes

## MLFF conventional-CV/final-selection revision plan

This release is architecture/documentation only. It records a new nine-gate MLFF revision and does
not change executable training, stopping, evaluation, verification, or export behavior.

The roadmap corrects the completed adaptive selector by restoring conventional statistical roles:

- fold models use a training-side nested checkpoint monitor for stopping/ranking/epoch selection;
- the rotating outer CV fold is untouched until one fold representative has already been frozen;
- lightweight target/replay monitors remain 256/512 configurations by default and control adaptive
  stopping, but the 30 meV/A target/replay acceptance thresholds no longer disqualify lightweight
  candidates;
- up to five epochs are ranked **per run**, then full checkpoint-selection validation applies the
  hard target/replay gates and chooses one representative;
- fold representatives are evaluated once on untouched outer folds and are never production-model
  candidates;
- only the four full-development final-seed representatives compete for the single production-best
  model; qualified final representatives may also be exported as an active-learning committee;
- shared CV folds remain the default across optimizer seeds so partition and optimizer variance can
  be separated; optional per-seed fold randomization is defined only as broader robustness sampling;
- per-run training/target/replay diagnostic histories and plots become planned auditable artifacts;
- final validation `D` is explicitly a model-selection domain, while locked test `E` remains one-shot
  post-freeze evidence and cannot trigger fallback; and
- historical ADAPT-MON1/STOP1/RANK1/EVAL1/VERIFY1 evidence remains readable under its original
  authority and is never silently reinterpreted.

The implementation order is `MLCV-ROLE1`, `MLCV-MON1`, `MLCV-STOP1`, `MLCV-RANK1`,
`MLCV-SELECT1`, `MLCV-AGG1`, `MLCV-FINAL1`, `MLCV-VERIFY1`, and `MLCV-MIGRATE1`.
