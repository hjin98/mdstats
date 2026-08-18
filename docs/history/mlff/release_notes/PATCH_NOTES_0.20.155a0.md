# mdstats 0.20.155a0 patch notes

## MLFF campaign seed extension

- Adds `mdstats-mlff-campaign extend-seed --seed N` for extending a completed conventional MLCV campaign with one additional optimizer seed before VERIFY1/production freeze.
- Requires `seed_mode = "optimizer_only"` and authenticates that the new DATA8 `MlcvRoleCatalog` is identical to the parent seeds, guaranteeing the same CV folds.
- Reuses DATA2-DATA6 plus the exact promoted fold-local DATA7 artifacts from completed parent variants (even if the transient DATA7 cache was cleaned), prior DATA8 variants, completed parent training runs, SELECT1 full evaluations, and AGG1 outer-fold evaluations.
- Trains only the appended seed's `K` folds plus final-development job, then rebuilds campaign-level AGG1/FINAL1 authority over the strict seed superset.
- Archives superseded campaign-level authority under content-addressed historical seed-extension records rather than deleting its provenance.
- Refuses extension after VERIFY1, locked-E, production publication, protocol freeze, or MLCV migration; frozen production authority requires a new campaign identity.
- Adds `--training-mode`, `--seed`, and `--selection-size` filters to `train` for targeted scheduling/resume.
- Seed extension is resumable and idempotent. A completed extension is a no-op; a new seed joins the committee only if it passes the existing qualification gates.
