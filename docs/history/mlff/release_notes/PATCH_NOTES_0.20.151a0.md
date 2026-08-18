# mdstats 0.20.151a0

## MLFF conventional-CV DATA8 path hotfix

`MLCV-SELECT1` previously treated the `relative_path` stored by job-local `MaceExtxyzArtifact` records as though it were relative to the complete DATA8 bundle root. DATA8 writes these records from each `jobs/<job_id>/` directory, so a recorded `target_checkpoint_full.xyz` actually lives at `jobs/<job_id>/target_checkpoint_full.xyz`. The evaluator consequently reported valid `V_i_full`/`D_full` artifacts as "missing or stale" before inference.

This release adds an explicit job-scoped DATA8 resolver and uses it for:

- SELECT1 complete target validation (`V_i_full` for folds, `D_full` for final-development jobs);
- AGG1 untouched outer-fold evaluation (`fold_evaluation.xyz`).

Historical absolute staging paths continue to use the existing promotion/rebase compatibility path. Path traversal outside the promoted job root is rejected. No scientific artifact identity, frame membership, checkpoint identity, threshold, score, or training protocol changes. Existing promoted DATA8 files and completed training runs remain reusable.
