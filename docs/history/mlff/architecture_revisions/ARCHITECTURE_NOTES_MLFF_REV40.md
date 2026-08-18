# MLFF architecture revision 40 — append-only optimizer-seed extension

## Purpose

A completed conventional MLCV campaign may need an additional optimizer realization after SELECT1/AGG1/FINAL1 has already qualified a committee. Re-running or cloning the complete campaign would waste the authenticated scientific evidence from the existing seeds. The new seed-extension path makes the campaign appendable before physical verification freezes production authority.

## User surface

```bash
mdstats-mlff-campaign --config campaign.toml extend-seed --seed 4
```

Optional disambiguators are `--training-mode` and `--selection-size`. `--dry-run` reports the extension without changing TOML or campaign state.

## Scientific contract

Seed extension is deliberately narrower than arbitrary campaign mutation.

1. The campaign must use `mlcv_nested_cv` and must already contain completed AGG1/FINAL1 committee evidence.
2. The requested training method must use `seed_mode = "optimizer_only"` with at least two CV folds. This keeps optimizer-seed variance separate from partition variance.
3. The extension currently requires one configured selection size; adding a method seed therefore creates exactly one new method/size variant rather than silently extending multiple learning-curve sizes.
4. VERIFY1, locked-E, production publication, generic protocol freeze, or MLCV migration authority forbids extension. Once physical/production authority exists, a new campaign identity is required.
5. After DATA8 materializes the new seed, its `MlcvRoleCatalog` digest must exactly equal the parent-seed role catalog. A mismatch fails before training.
6. The appended seed is not guaranteed committee membership. It must independently pass the existing fold robustness, target-error, replay-retention, and FINAL1 qualification gates.

## Evidence reuse and lineage

The parent campaign plan and campaign-level derived authority are preserved under content-addressed historical seed-extension keys before the canonical campaign is reopened. Run-local evidence remains canonical because the original run-plan digests do not change:

- training execution/checkpoint inventories,
- lightweight ranking records,
- SELECT1 run-selection records,
- full candidate evaluations,
- AGG1 outer-fold target evaluations.

Campaign-level records are rebuilt because their lineage includes the campaign-plan digest:

- MLCV lifecycle authority,
- per-seed CV aggregates,
- campaign CV aggregate,
- FINAL1 final-seed selection,
- FINAL1 committee/member records.

This means adding seed 4 to a three-seed/three-fold campaign requires only four new MACE training runs (folds 0–2 plus final) and the new seed's SELECT1/outer-fold inference. The transient `.mdstats/data7-cache` is not required to survive: promoted DATA7 archives are authenticated and registered as exact reusable recipes before the new variant is built. Seeds 1–3 are authenticated and reused rather than retrained or reevaluated.

## Operational sequence

`extend-seed` is a resumable synchronous orchestrator:

1. validate the completed parent campaign and absence of frozen production authority;
2. atomically append the seed to the selected nested method table in `campaign.toml`, preserving comments;
3. archive the parent campaign-level authority and reopen the campaign;
4. rerun `doctor` against the changed TOML;
5. run incremental `prepare`, which reuses DATA2–DATA6, re-registers verified promoted DATA7 archives from completed parent variants for exact recipe reuse, reuses existing DATA8 variants, and materializes only the new seed variant;
6. authenticate identical MLCV fold roles;
7. rerun preflight for the expanded DATA8 matrix;
8. invoke filtered `train --training-mode ... --selection-size ... --seed ...` so only the new runs are scheduled;
9. invoke complete `evaluate`; prior run-local records are reused, and AGG1/FINAL1 are regenerated over the strict seed superset;
10. persist the extension outcome (`complete_qualified` or `complete_not_qualified`) and the child campaign/FINAL1 digests.

Re-running the same extension command resumes an interrupted extension. A completed extension is a no-op.

## Training filter extension

The public `train` command now accepts `--training-mode`, `--seed`, and `--selection-size` filters in addition to `--run-id` and `--max-runs`. This is independently useful for targeted restart/maintenance and is the mechanism used by the seed-extension scheduler.
