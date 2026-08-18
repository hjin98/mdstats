# mdstats 0.20.177a0 - LOCKED-TEST2

This release closes the post-0.20.162 MLFF production-selection revision with the one-shot locked post-freeze test and final byte-preserving production publication.

## Implemented

- Added `LOCKED-TEST2` as a strictly post-SELECT2 authority. The sealed target `locked_interpolation_test` role is exposed only after SELECT2 freezes one candidate.
- Locked evidence can only accept or reject that exact frozen candidate. It has no replay, ranking, fallback, checkpoint rescue, target-size selection, retraining, or alternate-seed authority.
- The default hard force-RMSE ceiling inherits the TRAIN2 full-target ceiling (30 meV/A for generated defaults). Optional locked-only ceilings are available for energy MAE/atom, worst-stratum force RMSE, force-error P99, and stress RMSE.
- Added immutable activation, result, and final-production records. Activation freezes the SELECT2 candidate, target role, locked-E bytes/membership/correlation blocks, policy, target-only model SHA-256, and ML-IAP SHA-256 before inference.
- Once activated, locked E is never rematerialized. Changed/missing locked bytes, policy, role lineage, candidate bytes, or correlation mapping fail closed and require a new campaign/protocol identity.
- Passing locked E atomically publishes the exact SELECT2 target-only model as `models/production_best.model` and the exact DEPLOY-authenticated ML-IAP artifact as `models/production_best-mliap_lammps.pt`. Failure publishes nothing and does not trigger fallback.
- Final publication is immutable: changed published bytes or mismatched recorded authority are treated as corruption, not a reason to silently replace the model.
- Updated the generated/example campaign configuration, CLI guide, canonical architecture manual, and current-gate specifications.

## Compatibility

Historical adaptive/MLCV campaigns remain under their original lifecycle and locked-test semantics. `LOCKED-TEST2` is part of the TRAIN2 policy generation only. The older version-pinned 0.20.140a0 specification debt is intentionally unchanged.

## Qualification

- Primary current-revision cross-gate regression: 210 passed, 1 expected external real-LTA-root skip.
- Additional DATA8/prediction-cache/production-materialization hardening: 39 passed.
- Final LOCKED-TEST2/current-gate sanity subset: 15 passed (overlaps the primary suite).
- Python `compileall` and public import/version checks pass.
- Architecture PDF preflight passes. The manual grows from 134 to 135 pages; LOCKED-TEST2 and revision-closure pages were rendered at high resolution and inspected without clipping, overlap, or broken glyphs. A full 50-DPI before/after render comparison completed successfully.

No real user campaign locked-E result is fabricated by this release. The implementation evaluates the sealed locked domain exactly once when the actual TRAIN2 campaign reaches SELECT2 freeze.
