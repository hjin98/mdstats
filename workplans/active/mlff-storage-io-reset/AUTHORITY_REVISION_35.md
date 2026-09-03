---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 35
status: reopened
supersedes_revision: 34
reviewed_executable_commit: 557d32b84c5934096c95ba3ea1d33ed1714d165b
reviewed_executable_tree: 349a8cb9ac7cee653733f397f196d1426f6a7726
reviewed_plan_commit: 55dcb26f1dd770b98e13b92ba088f93d2da3c371
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_14.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
plan_review_disposition: amended-resealed
---

# Storage/I-O reset authority — Revision 35

Revision 35 is a final independent review of the Revision-34 implementation handoff against the actual current mutation, trust, cleanup-session, archive/restore/dedup/maintenance and acceptance owners. Revision 30 remains the accepted closed design. Revision 35 does not reopen P1-P7 science/currentness, owner-driven storage architecture, CampaignStore ownership, P5 proof architecture, archive/dedup/restore/control-plane architecture, Python `>=3.10`, or the accepted descriptor-pinned POSIX threat boundary.

## Current normative handoff

Implementation reads only:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_14.md` — **complete Revision-35 bounded implementation and acceptance contract**;
5. `AUTHORITY.md` only as canonical navigation/status.

Revision 31-34 review/authority files are historical provenance. Revision 35 consolidates every still-binding correction so Implementation does not need to reconstruct prior review history.

## Plan-review findings incorporated into Revision 35

Revision 34 correctly identified the remaining broad safety/truth surfaces but was not yet lossless enough for implementation. Revision 35 closes the handoff gaps by:

- extending mutation-time mount ownership from nested directory children to the actual opened descriptor for both top-level destructive roots and descendants across P7, generic and certified-common cleanup;
- replacing post-hoc pathname-existence inference after `durable_unlink()` with direct transition-aware single-file mutation truth;
- carrying typed/current owner authority through individually-authorized common-member final mutation so an authorized regular file cannot be spent on a replacement symlink/directory/special node;
- extending close/finalization failure semantics through P7/generic recursive descriptors, `ReleasedAttemptSession.invalidate()/close()`, and `_cleanup_engine()` session finalization;
- separating P7 typed partial contradiction (loop continues, same attempt withheld, independent attempt proceeds) from exceptional post-mutation failure (action recorded, execution stops, cause propagates);
- making `StorageExecutionResult.mutated` the explicit cross-engine exception-time mutation fact and naming the current persistent transition points in cleanup, archive creation/hot reclamation/restore, deduplication and campaign-state maintenance;
- preserving engine-specific action/phase evidence instead of forcing cleanup removal outcomes onto non-removal engines;
- retaining public remover compatibility while requiring one canonical consequential recursive implementation;
- broadening exact-candidate affected regression to every maintained archive/restore/dedup/maintenance consumer actually implicated by the final implementation.

## Preserved implementation state

Preserve the conforming work already present: the shared cleanup `MutationLedger`, zero-credit mutation truth, exact per-action reclaimed bytes, descriptor-relative/no-follow child recursion, trust-owned no-follow directory acquisition, complete P7 target identity, real two-attempt fixture, deterministic exact-byte oracle, resealed/damaged final-authority acceptance, repaired interruption failpoints, and the updated storage specification.

The reviewed executable remains **NO-PASS** until the Revision-35 implementation and exact-candidate acceptance obligations close.

## Authority

**Accepted design:** **CLOSED / implementation-ready under Revision 30.**

**Current bounded implementation handoff:** **Revision 35 / reopened.**

**Reviewed executable:** **NO-PASS / reopened pending Revision 35.**
