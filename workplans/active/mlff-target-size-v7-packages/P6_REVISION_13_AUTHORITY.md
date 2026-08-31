---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 13
amended_date: 2026-08-31
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
reviewed_candidate_commit: e1eb4911069a5003c9d4195a52daf36dc0f813e1
reviewed_candidate_tree: d8ea290af256a0f6938206e26c12b0398b7a8d2f
reviewed_executable_commit: 3212201e70335724fd0fa345842b6949587b931e
reviewed_executable_tree: c1638420a073ebcc5310da4be765202846375f21
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 13 — authoritative composed acceptance-closure contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 13 supersedes revision 12 as the current Design -> Implementation handoff.

## Authoritative supplied artifact set

Read the following as one composed P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 compatibility.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — public/config/docs cleanup and compatibility closure.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral P1-P5 handoff and conservative successor quarantine.
5. `P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md` — final-owner/config/completion/storage/qualification closure contract.
6. `P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md` — CV-plan-free DATA5, evidence-authenticated completion, current-generation storage quarantine, A/B/C qualification.
7. `P6_REVISION_9_FINAL_IMPLEMENTATION_CLOSURE_AMENDMENT.md` — accepted multi-seed final-production interruption/restart closure.
8. `P6_REVISION_10_STORAGE_PUBLIC_SURFACE_FINAL_CLOSURE_AMENDMENT.md` — truthful safe/cache public/config/report surface and transitional storage tightening, except where later revisions supersede its cache/run-cleanup premises.
9. `P6_REVISION_11_CURRENT_CACHE_OWNER_CLOSURE_AMENDMENT.md` — no P6/P7 cache-family eviction, cache retention/deferment, neutral report wording, and real P3/P5 retention evidence.
10. `P6_REVISION_12_SAFE_CLEANUP_OWNER_FINAL_CLOSURE_AMENDMENT.md` — removal of retired `workspace/runs` PID/path cleanup authority and cleanup-triggered SHA-256 receipt pruning.
11. `P6_REVISION_13_FINAL_PROXY_PROOF_AND_EXECUTION_EVIDENCE_CLOSURE_AMENDMENT.md` — current final acceptance-only closure: repair two non-discriminating proxy-proof tests and produce fresh exact-candidate assembled execution evidence.

Precedence is revision 13 over revision 12 over revision 11 over revision 10 over revision 9 over revision 8 over revision 7 over revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All unrelated obligations remain binding.

## Revision-13 review disposition

Independent review accepts the revision-12 production-source correction. The reviewed executable no longer derives cleanup authority from historical `workspace/runs`/PID conventions and no longer prunes SHA-256 receipts through safe/cache cleanup. Current storage/public documentation is materially aligned with that conservative contract.

P6 remains **NO PASS** solely because required acceptance evidence is not yet proxy-proof/executed at the frozen boundary:

- the receipt-retention test uses 20 rows although the rejected pruner activates only above 100,000 rows;
- the referenced-external-record retention test uses a small inline mapping and a young manually created object rather than a stale real `CampaignStore` external pointer;
- the exact revision-12 candidate has no fresh recorded A/B/C, real lifecycle, and broader/full CPU-safe execution evidence; the tracked evidence document remains revision 4.

Revision 13 therefore reopens **test adequacy and final executable evidence only**. Do not change accepted runtime/scientific/storage semantics unless the corrected tests expose a real defect.

## Revision-13 PASS boundary

P6 revision-13 PASS requires:

```text
all accepted revision-12 runtime/scientific/storage/public behavior preserved
+ SHA-256 retention acceptance exceeds the real 100,000-row pruning boundary
+ stale real CampaignStore external-pointer retention is proven while a stale orphan sibling is reclaimed
+ inherited R8-R12 focused acceptance PASS
+ P3/P5 owner retention PASS
+ revision-9 two-seed interruption/resume/integrity PASS
+ exact P5A6 compatibility A PASS
+ fresh final-P6 close/reopen/restart B PASS
+ V5/V6 reject-before-reuse C PASS
+ real parser lifecycle PASS
+ final broader/full CPU-safe regression executed on the exact tested tree with zero new P6-attributable nonpasses
+ P6_IMPLEMENTATION_EVIDENCE.md reconciled to revision 13 with exact tested commit/tree and commands/results
+ affected documentation/PDF workflow PASS
```

Only an independently reviewed **P6 revision-13 PASS** opens P7. P7 completion then opens the separate post-P7 storage/I-O reset gate.
