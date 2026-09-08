---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 10
amended_date: 2026-08-31
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
reviewed_candidate_commit: 93150315466671334bf0ac5ed1f187d8cc304407
reviewed_candidate_tree: bc88d82ae3f9db8996da39d8af0735d9a9e7a25c
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 10 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 10 supersedes revision 9 as the current Design -> Implementation handoff.

## Authoritative supplied artifact set

Read all of the following as one composed P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 current-workspace compatibility requirement, except where later revisions tighten its evidence mechanism.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — public/config/docs cleanup, compatibility-proof hardening, and corrected P6 closure semantics.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral P1-P5 handoff and conservative quarantine pending the post-P7 storage reset.
5. `P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md` — final-owner/config/completion/storage/qualification closure contract.
6. `P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md` — CV-plan-free fresh DATA5, evidence-authenticated final-production completion, current-generation STOR quarantine, genuinely distinct A/B/C qualification, and tied documentation/dependency corrections.
7. `P6_REVISION_9_FINAL_IMPLEMENTATION_CLOSURE_AMENDMENT.md` — accepted multi-seed final-production interruption/restart closure plus prior storage tightening.
8. `P6_REVISION_10_STORAGE_PUBLIC_SURFACE_FINAL_CLOSURE_AMENDMENT.md` — final remaining storage/public-surface repair: truthful generated guidance, removal of the hidden cleanup alias, strict safe-vs-cache semantics, conservative frame-cache retention, owner/liveness-guarded inactive-run cache eviction, and current-generation storage-report classification.

Precedence is revision 10 over revision 9 over revision 8 over revision 7 over revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All other obligations remain binding.

## Revision-10 review disposition

Independent review of the revision-9 candidate accepted the P5 multi-seed restart/integrity repair. Revision 10 therefore **does not reopen or re-specify P5** beyond preserving that accepted behavior and rerunning affected/final acceptance where `_campaign_cli_core.py` changes can interact with lifecycle/status/storage tests.

The sole remaining blocking area is transitional storage/public-surface conformance. Implementation must follow `P6_REVISION_10_STORAGE_PUBLIC_SURFACE_FINAL_CLOSURE_AMENDMENT.md` exactly for that surface.

## Scope and PASS boundary

P6 remains a **cleanup/cutover functional-closure package**. It does not implement P7 downstream publication/qualification and does not implement `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

Revision-10 P6 PASS requires:

```text
all accepted revision-9 scientific/P5 ownership and restart behavior preserved
+ generated config/help/guide/spec expose one truthful safe|cache transitional contract
+ no unsupported hidden top-level cleanup alias
+ safe cleanup has zero acceleration-cache eviction
+ cache cleanup uses real current owner/liveness authorization
+ frame-cache retained by safe and cache during P6
+ inactive-run checkpoint-model-cache removable only by cache
+ active-run cache retained
+ historical path names remain non-authoritative for deletion
+ storage report is advisory and contains no retired STOR/recompute/compact/protocol-freeze mutation policy
+ exact P5A6 unchanged compatibility
+ independent fresh-P6 production/restart
+ V5/V6 reject-before-reuse
+ stage-local and final affected regression/integration closure
```

Only an independently reviewed **P6 revision-10 PASS** opens the P7 implementation gate. P7 completion then opens the separate post-P7 storage/I-O reset gate.