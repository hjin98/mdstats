# mdstats 0.20.208a0 - TARGET-DATA2C-MVMIGRATE1

This release implements the generated-policy migration control plane without fabricating the GPU evidence intentionally deferred to the final release.

## Added

- `TargetMultiViewMigrationPolicy`, paired legacy-vs-MV learning-control records, and `TargetMultiViewMigrationPlan`.
- TARGET-DATA2C v5 candidate construction from the exact REPAIR1 master sequence with independent TARGET-DATA2B/DATA2A requalification.
- Fixed generated candidate sizes `128..16384`, minimum four hard qualifiers, and explicit prohibition of revision-64 dynamic rescue in v5 semantics.
- Generation-separated TARGET-DATA2D v3 and TARGET-DATA2E v3 schemas.
- Campaign persistence for the MVMIGRATE1 latch and authenticated v5 candidate, with content-addressed restart rebuilding.

## Activation rule

The migration is **not activated by this CPU/control-plane package**. Activation requires both (1) passed FINAL-GPU1 same-N legacy-vs-MV TRAIN2/EVAL2 learning controls at the MVQUAL1 frozen control sizes and (2) a passed SIZE-FIDELITY2 qualification whose `gpu_qualification_status` is exactly `passed`. Until then, revision-64 TARGET-DATA2C v4 / TARGET-DATA2D v2 / TARGET-DATA2E v2 remain live.

This is deliberate: a deferred or CPU-only record cannot masquerade as final accelerator qualification. Once final GPU evidence is added, only the migration plan and its v5 candidate need to be revalidated/rebuilt; DATA6, TARGET-DATA2A/B, MVIDX1, MVSEL1, and REPAIR1 remain reusable when their content digests are unchanged.

## Unchanged

DATA8 membership, the independent 0.95 hard-coverage rule, e3nn source/DATA6 policy, CuEq TRAIN2 policy, and the final-release GPU deferral policy are unchanged.

Architecture revision advances to 75 and dependency-graph schema to 57. Next action: `FINAL-GPU1` consolidated workstation qualification and atomic migration activation on pass.
