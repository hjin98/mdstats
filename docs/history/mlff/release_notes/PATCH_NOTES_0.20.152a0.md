# mdstats 0.20.152a0 patch notes

## MLCV SELECT1 R_full runtime-path hotfix

`MLCV-SELECT1` previously validated `replay_full_validation_artifact.path` directly. That path is frozen when DATA8 is built and can point into the temporary DATA8 staging tree. After DATA8 is promoted into the campaign materialization tree, the staging directory may no longer exist even though the authenticated replay file is present at `shared/replay/full_true_replay_validation.xyz`.

The evaluator now resolves `R_full` with the existing bundle-scoped DATA8 runtime rebase helper before checking file existence and SHA-256. This mirrors the already-correct training-time R_light/R_full handling.

No scientific artifact is regenerated and no training/evaluation policy changes. Existing DATA8 bundles and completed training runs can be reused; rerun `mdstats-mlff-campaign evaluate`.
