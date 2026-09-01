---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 12
amended_date: 2026-08-31
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
reviewed_candidate_commit: 79b7cf372df4637d6e8bfccfb31071da4fba8d76
reviewed_candidate_tree: 444e2c8e30be94b2e7a326d80411bb8b4e4c753b
reviewed_executable_commit: a051850f3a0cf1bd6c3392cb097e868b92f382f8
reviewed_executable_tree: ad3e9bb2fb5e1436d2b92cd69f7aa7db41cda3a0
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 12 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 12 supersedes revision 11 as the current Design -> Implementation handoff.

## Authoritative supplied artifact set

Read the following as one composed P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 compatibility.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — public/config/docs cleanup and compatibility closure.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral P1-P5 handoff and conservative successor quarantine.
5. `P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md` — final-owner/config/completion/storage/qualification closure contract.
6. `P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md` — CV-plan-free DATA5, evidence-authenticated completion, current-generation storage quarantine, A/B/C qualification.
7. `P6_REVISION_9_FINAL_IMPLEMENTATION_CLOSURE_AMENDMENT.md` — accepted multi-seed final-production interruption/restart closure.
8. `P6_REVISION_10_STORAGE_PUBLIC_SURFACE_FINAL_CLOSURE_AMENDMENT.md` — truthful safe/cache public/config/report surface and transitional storage cleanup tightening, except where revisions 11-12 supersede its cache/run-cleanup premises.
9. `P6_REVISION_11_CURRENT_CACHE_OWNER_CLOSURE_AMENDMENT.md` — no P6/P7 cache-family eviction, cache retention/deferment, neutral report wording, and real P3/P5 retention evidence.
10. `P6_REVISION_12_SAFE_CLEANUP_OWNER_FINAL_CLOSURE_AMENDMENT.md` — final current-owner closure for safe/cache: remove retired `workspace/runs` PID/path deletion authority, remove storage-cleanup-triggered SHA-256 receipt eviction, reconcile remaining safe actions/docs, and require final executable acceptance evidence.

Precedence is revision 12 over revision 11 over revision 10 over revision 9 over revision 8 over revision 7 over revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All unrelated obligations remain binding.

## Revision-12 review disposition

Independent review of the revision-11 candidate accepts the revision-11-specific cache/public-surface correction: cache-tier positive deletion was removed, checkpoint/frame/historical caches are retained/deferred, report wording is neutralized, and the fake PID cache-deletion acceptance model was replaced by retention tests through current P3/P5 owner trees.

The candidate is nevertheless **NO PASS** because public safe cleanup still reaches retired `workspace/runs` execution conventions. `_campaign_cleanup()` enumerates `paths.runs`, `_active_training_run_ids()` interprets `active_process.json` PID state and may unlink stale markers, and `_cleanup_obsolete_training_runtimes()` deletes `obsolete-runtime-*` subtrees. The P6 cutover separately declares `campaign_execution` retired/absent, so this path has no surviving current semantic owner. The same safe path also calls `CampaignStore.compact()`, which invokes `prune_sha256_receipts()` and therefore evicts an acceleration cache despite the frozen safe zero-cache-eviction contract.

Revision 12 reopens only this final storage-cleanup owner surface. It does not reopen accepted P1-P5 science, P5 restart, P7 behavior, or successor-storage architecture.

## Scope and PASS boundary

P6 remains a cleanup/cutover functional-closure package. It does not implement P7 downstream publication/qualification and does not implement `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

Revision-12 P6 PASS requires:

```text
all accepted revision-11 scientific/P5/cache/public behavior preserved
+ no safe/cache deletion authority derived from workspace/runs, active_process.json, PID state, age, or obsolete-runtime-* naming
+ historical workspace/runs traps retained by both tiers
+ safe/cache storage cleanup performs zero acceleration-cache eviction, including no SHA-256 receipt pruning
+ every remaining safe destructive action is backed by a surviving current owner and zero-capability-loss proof
+ current P3/P5 owner trees remain protected
+ exact P5A6 compatibility A PASS
+ fresh final-P6 close/reopen/restart B PASS
+ V5/V6 reject-before-reuse C PASS
+ real parser lifecycle PASS
+ stage-local and final broader/full CPU-safe affected regression/integration executed on the exact assembled candidate
+ affected docs/PDFs current
```

Only an independently reviewed **P6 revision-12 PASS** opens P7. P7 completion then opens the separate post-P7 storage/I-O reset gate.