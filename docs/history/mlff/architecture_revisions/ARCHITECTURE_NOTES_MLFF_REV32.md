# MLFF architecture revision 32 - conventional CV and final-model selection roadmap

This architecture-only revision records the next gated MLFF correction after the completed
ADAPT-PREC1 -> ADAPT-MIGRATE1 cycle. It does **not** change production runtime behavior yet.

The new `MLCV-ROLE1` -> `MLCV-MIGRATE1` roadmap restores conventional nested cross-validation and
separates checkpoint selection from outer-fold evidence and final-model deployment:

1. `MLCV-ROLE1` - freeze training, nested checkpoint-selection, outer CV, final-validation `D`,
   locked-test `E`, and replay roles with fail-closed anti-leakage lineage;
2. `MLCV-MON1` - use fold-local nested lightweight/full checkpoint monitors, final `D_light/D_full`,
   TRUE_DFT replay light/full monitors, and diagnostic training-error histories;
3. `MLCV-STOP1` - keep 80% target-success and 120% replay-exhaustion as lightweight stopping
   heuristics only; absolute 30 meV/A acceptance is reserved for full validation;
4. `MLCV-RANK1` - rank every finite epoch and keep up to five candidates per independent run without
   lightweight hard-threshold disqualification;
5. `MLCV-SELECT1` - select fold representatives on nested full validation and final representatives
   on full `D`, always with full TRUE_DFT replay validation and component-wise hard gates;
6. `MLCV-AGG1` - evaluate each frozen fold representative exactly once on its untouched outer fold
   and publish conventional CV robustness statistics;
7. `MLCV-FINAL1` - allow only full-development final-seed representatives to compete for production;
   export exactly one production-best model plus the qualified final-seed committee when requested;
8. `MLCV-VERIFY1` - restrict physical-verification fallback to qualified final models and activate
   locked `E` exactly once after the production candidate is frozen; and
9. `MLCV-MIGRATE1` - preserve historical adaptive evidence while closing new schema/restart/storage
   authority and end-to-end qualification.

The generated default remains multi-head replay only with four optimizer seeds and three common CV
folds plus one final fit per seed (`4 x (3 + 1) = 16` runs). Shared folds remain the default so fold
variance and optimizer-seed variance stay separable. Per-seed fold randomization may later be exposed
as a robustness mode, but it is not treated as a mechanism for diversifying full-data final models.

A critical statistical correction is explicit: the top-five fold checkpoints are selected using a
nested full checkpoint monitor carved from the fold's training side. The rotating outer CV fold is
never used to stop, rank, or select an epoch. It is evaluated only after the fold representative is
frozen. This preserves the DATA5 anti-leakage principle already stated in the canonical manual.

Canonical details are in `docs/arch_manuals/mlff_training_data_architecture.{md,pdf}`.
