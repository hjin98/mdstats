# mdstats 0.20.111a0 patch notes

This release closes MLFF gate STOR1.

## Read-only storage report

`mdstats-mlff-campaign storage` inventories the campaign workspace and writes `results/storage-report.json` only when the report destination passes ownership/containment checks. The report distinguishes path-logical bytes, inode-deduplicated allocated physical bytes, and unique-inode logical bytes; classifies artifact families and retention roles; records protected configured inputs and symlink escapes; and lists the largest files/directories. No reclamation is performed.

## Ownership boundary hardening

Configured training/source, foundation, replay, true-label, and campaign configuration paths remain protected user/reference inputs even when nested inside the workspace. Existing cleanup and post-evaluation checkpoint pruning now require the same campaign ownership boundary before deleting, compacting SQLite, or writing cleanup diagnostics/reports. A path recorded in campaign state is not deletion authority. Campaign-owned symlink objects can be unlinked safely, but external targets are never traversed or deleted.

## Next gate

STOR2 will qualify authenticated model-state-only evaluation capsules for completed non-resume checkpoints. STOR1 deliberately introduces no new destructive cleanup tier.
