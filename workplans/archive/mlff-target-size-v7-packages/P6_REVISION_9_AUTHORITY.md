---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 9
amended_date: 2026-08-31
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
reviewed_candidate_commit: 950acf577de67199828e0f94389fb6d8d4c4305d
reviewed_candidate_tree: c8ddbef8b3a1a7cecde3d58d330cb57dc6d3991d
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 9 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 9 is the current implementation package and supersedes revision 8 as the Design -> Implementation handoff.

## Authoritative supplied artifact set

Read all of the following as one composed P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 current-workspace compatibility requirement, except where later revisions tighten its evidence mechanism.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — public/config/docs cleanup, compatibility-proof hardening, and corrected P6 closure semantics.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral P1-P5 handoff and conservative quarantine pending the post-P7 storage reset.
5. `P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md` — final-owner/config/completion/storage/qualification closure contract.
6. `P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md` — CV-plan-free fresh DATA5, evidence-authenticated final-production completion, current-generation STOR quarantine, genuinely distinct A/B/C qualification, and tied documentation/dependency corrections.
7. `P6_REVISION_9_FINAL_IMPLEMENTATION_CLOSURE_AMENDMENT.md` — final implementation closure after revision-8 review: remove retired STOR semantics from the reachable safe/cache and automatic-cleanup authority itself, reconcile the current storage docs/help, and prove two-or-more-seed partial final-production interruption/resume through the real P5 owner with missing-run-only execution.

Precedence is revision 9 over revision 8 over revision 7 over revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All other obligations remain binding.

## Revision-9 review disposition

The revision-8 candidate substantially closed the prior DATA5/CV, plan-versus-completion, and producer-lineage defects. Revision 9 therefore does **not** reopen those designs. It preserves the accepted revision-8 outcomes and closes only two remaining implementation blockers:

1. current supported storage cleanup still contains retired STOR-era stage/path/capability deletion semantics; and
2. final-production acceptance still lacks a real proper-subset state because the committed production fixture uses one required seed.

Implementation must follow `P6_REVISION_9_FINAL_IMPLEMENTATION_CLOSURE_AMENDMENT.md` exactly for those surfaces. If its stronger real-owner tests expose additional local consequences, repair them under the same frozen architecture. Reopen Design only on the explicit evidence triggers in revision 9.

## Scope and PASS boundary

P6 remains a **cleanup/cutover functional-closure package**. It does not implement P7 downstream publication/qualification and does not implement `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

Revision-9 P6 PASS requires:

```text
all revision-8 accepted ownership/scientific repairs preserved
+ fresh current DATA5 remains CV-plan-free
+ P5 remains sole selected-set CV owner
+ final-production plan remains distinct from authenticated completion
+ >=2-seed proper-subset interruption/restart proven through real P5 owners
+ resume executes only missing required final runs
+ corrupt/mismatched required run evidence fails closed
+ current safe/cache cleanup is current-owner-proven and fail-toward-retention
+ no evaluate/verify/preflight/DATA7-DATA8/old-STOR destructive authority remains reachable
+ current storage help/spec/guide describe only the transitional P6/P7 surface
+ exact P5A6 unchanged compatibility
+ independent fresh-P6 production/restart
+ V5/V6 reject-before-reuse
+ stage-local and final affected regression/integration closure
```

Only an independently reviewed **P6 revision-9 PASS** opens the P7 implementation gate. P7 completion then opens the separate post-P7 storage/I-O reset gate.