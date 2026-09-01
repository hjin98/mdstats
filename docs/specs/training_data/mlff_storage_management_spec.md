# MLFF campaign storage-management specification (Transitional P6/P7 Contract)

Status: Accepted transitional specification under P6/P7 governance. Historical STOR1-STOR5 design notes are archived in `docs/history/mlff/STOR1_STOR5_HISTORICAL_DESIGN.md`. Consequential storage transformations are deferred to the unified storage reset workplan `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Purpose

This specification defines the authoritative transitional storage-management contract for MLFF training data campaigns during the P6/P7 lifecycle. Storage policy is strictly subordinate to scientific provenance, training restartability, and user data ownership.

## Non-negotiable protections

1. **External directory immutability**: User-supplied source datasets, training sets, replay trajectories, and true-label reference material located outside the campaign workspace are read-only inputs. Campaign storage operations shall never delete, truncate, rewrite, rename, or relocate external paths.
2. **Ownership and boundary enforcement**: A path reference appearing in TOML configuration, SQLite state, JSON metadata, or an artifact manifest does not confer deletion authority. Destructive operations are strictly restricted to campaign-owned artifacts that pass physical containment and ownership boundary validation.
3. **Symlink traversal protection**: A symlink object located inside the campaign workspace may be unlinked only if campaign-owned, but cleanup shall never traverse external symlink targets.
4. **Production artifact preservation**: Final selected production models, production checkpoints, and selection/verification evidence are retained by default.
5. **Fail-toward-retention under incomplete lifecycle**: In the presence of incomplete stages, active training jobs, unverified evidence, or ambiguous ownership boundaries, cleanup fails closed toward full artifact retention.

---

## 1. Storage Accounting (`storage report`)

The `storage report` command is strictly read-only. It inspects the campaign workspace and produces `results/storage-report.json` reporting:
- Logical allocated bytes and unique-inode bytes;
- File counts and artifact family distributions;
- Protected input boundaries and external reference validations;
- Reconstructable cache sizes versus retained scientific evidence.

No files are modified or removed during accounting operations.

---

## 2. Safe and Cache Cleanup (`storage cleanup`)

Current-generation campaigns support two non-destructive / low-consequence cleanup tiers:

### Default / Safe Tier (`--tier safe`)
- Targets only unreferenced orphaned external database records and performs bounded diagnostic database housekeeping.
- Guarantees zero loss of scientific capability, evaluation state, training restartability, or acceleration caching (zero acceleration-cache eviction, including no SHA-256 receipt pruning).
- Every safe cleanup event appends an authenticated record to `results/cleanup-manifest.jsonl` with an empty capability-loss set.

### Cache Tier (`--tier cache`)
- Includes the safe tier and is reserved for cache-policy intent in the public cleanup vocabulary.
- In P6/P7, no cache-family eviction is authorized because current P3/P5 do not expose a storage-owner/reconstruction contract suitable for safe eviction; both `frame-cache` and `checkpoint-model-cache` are conservatively retained by both safe and cache tiers.
- Consequential cache ownership/eviction, leases, archive, deduplication, admission, and cross-owner storage design remain deferred to `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

---

## 3. Quarantined Operations Deferred to Post-P7 Storage Reset

Consequential historical storage tiers and physical transformations change reanalysis, continuation, or file-structure semantics and are **not supported** for current P6/P7 generation campaigns:
- `storage cleanup --tier recompute`
- `storage cleanup --tier compact`
- `storage cleanup --tier archive`
- `storage deduplicate --apply`
- `storage archive create`
- `storage archive restore`

When invoked on a current-generation campaign, these commands fail closed with a clear `CampaignCliError` indicating that consequential storage transformation is deferred to `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.
