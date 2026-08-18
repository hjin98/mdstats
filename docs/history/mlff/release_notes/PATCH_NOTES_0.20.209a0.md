# mdstats 0.20.209a0 patch notes

## FINAL-GPU1 v2 release handoff

- Upgrade the immutable FINAL-GPU1 authority to policy/qualification schema v2 and preflight v7.
- Add `SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION` and `TARGET_DATA2C_MVMIGRATE1_LEARNING_CONTROLS` as typed must-pass release blockers.
- Add source-tree assemblers `tools/qualify_mlff_size_fidelity2.py` and `tools/qualify_mlff_target_mv_learning_control.py`.
- Require the registered evidence content digests to equal the typed qualification-record digests and bind both migration records to one dataset identity.
- Preserve all previous must-pass, measure-only, optional, release-artifact, and CUEQ-runtime provenance checks.

## Atomic generated-policy migration

- Add `tools/activate_mlff_target_mv_migration.py` with fail-closed dry-run and explicit `--apply` modes.
- Recompute the MVMIGRATE1 plan from final GPU evidence instead of trusting a hand-edited activation flag.
- Rebuild and validate TARGET-DATA2C v5 from the exact REPAIR1 master order and build TARGET-DATA2D v3 with the frozen four-qualifier minimum.
- Publish v5/v3 plus the final evidence and activation receipt in one SQLite transaction while preserving the historical v4 ladder.
- Invalidate stale TARGET-DATA2E production-decision and prepare-restart aliases rather than allowing mixed generations.
- Make prepare restart receipts track optional final-GPU/migration authorities when present.

Positive GPU qualification remains pending the final workstation run; this package does not claim a GPU pass.
