# mdstats 0.20.78a0: verification from completed models in interrupted campaigns

## Completion-aware evidence

`evaluate` no longer requires the entire configured training matrix to finish before useful evidence can be produced. It discovers successfully completed runs, recovers valid child-complete artifacts when the campaign parent missed the final database commit, evaluates their selected checkpoints, and groups them by exact method, selection size, and optimizer seed.

Evidence is classified conservatively:

- **complete variant**: every configured cross-validation fold and the final-development run for one method/size/seed are complete;
- **partial cross-validation**: at least two configured folds are complete, allowing a reduced fold-to-fold estimate;
- **single model**: only one completed fold or final model is available, so no cross-fold estimate is claimed.

The corresponding `verify` command runs bounded NVE stability checks only on the exported completed models. Partial and single-model results carry explicit warnings and remain interim evidence. They do not create a production protocol freeze or authorize deployment.

## Scope controls

Interim evaluation may be restricted to an exact completed group:

```bash
mdstats-mlff-campaign --config campaign.toml evaluate \
  --training-mode multihead_replay --seed 1
```

`--selection-size` further narrows the group. `evaluate --require-complete` restores all-or-nothing behavior. `verify --require-frozen` refuses interim evidence and requires the fully frozen production committee.

If additional training runs complete after an interim evaluation, `verify` fails closed and asks the user to rerun `evaluate`; it never silently verifies a stale subset. Exported model bytes are SHA-256 checked before bounded MD.

## Preservation and restart

Interim evaluation does not prune checkpoints, delete restart state, or mark the full evaluation stage complete. Completed runs remain checksum-verified and are skipped by future `train` calls; unfinished runs can resume normally. Once the whole configured matrix finishes, ordinary `evaluate` performs the full protocol comparison, committee export, production freeze, and normal post-evaluation cleanup.
