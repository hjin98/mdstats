---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 7
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 7 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 7 is the current implementation package and the final Design handoff for the next P6 implementation round.

## Authoritative supplied artifact set

Read all of the following as one composed P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 current-workspace compatibility requirement, except where later revisions tighten its evidence mechanism.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — public/config/docs cleanup, compatibility-proof hardening, and corrected P6 closure semantics.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral P1-P5 handoff and conservative quarantine pending the post-P7 storage reset.
5. `P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md` — final independent-review closure: remove pre-target CV ownership, remove orphan current configuration, distinguish final-production plan from completion, close transitional storage behavior, separate compatibility producer lineages, reconcile documentation ownership, and freeze final acceptance.

Precedence is revision 7 over revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All other obligations remain binding.

## Scope

P6 remains a **cleanup/cutover functional-closure package**. It does not implement P7 downstream qualification and does not implement `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

The revision-7 PASS boundary is:

```text
clean current P1-P5 scientific/currentness ownership
+ truthful current public/config/documentation surface
+ completed final-production evidence rather than plan-only completion
+ conservative storage-neutral P3/P5 handoff
+ exact P5A6 compatibility
+ independent P6-created self-restart
+ V5/V6 reject-before-reuse
+ affected regression/integration closure
```

Only an independently reviewed revision-7 P6 PASS opens the P7 implementation gate. P7 completion then opens the separate storage/I-O reset gate.
