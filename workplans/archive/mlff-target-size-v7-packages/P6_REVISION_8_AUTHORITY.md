---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 8
amended_date: 2026-08-31
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
reviewed_candidate_commit: 2740ed6e0c638808306bcd889119bb6d240658b4
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 8 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 8 is the current implementation package and supersedes revision 7 as the Design -> Implementation handoff.

## Authoritative supplied artifact set

Read all of the following as one composed P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 current-workspace compatibility requirement, except where later revisions tighten its evidence mechanism.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — public/config/docs cleanup, compatibility-proof hardening, and corrected P6 closure semantics.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral P1-P5 handoff and conservative quarantine pending the post-P7 storage reset.
5. `P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md` — final-owner/config/completion/storage/qualification closure contract.
6. `P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md` — precise repairs after independent review of the revision-7 implementation: CV-plan-free fresh DATA5, evidence-authenticated final-production completion, current-generation STOR quarantine, genuinely distinct A/B/C qualification, and tied documentation/dependency corrections.

Precedence is revision 8 over revision 7 over revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All other obligations remain binding.

## Scope and PASS boundary

P6 remains a **cleanup/cutover functional-closure package**. It does not implement P7 downstream qualification and does not implement `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

Revision-8 P6 PASS requires:

```text
clean current P1-P5 ownership
+ fresh current DATA5 with no pre-selection CV plans
+ P5-only selected-set CV construction
+ truthful evidence-authenticated final-production completion
+ conservative transitional storage free of retired destructive lifecycle policy
+ exact P5A6 unchanged compatibility
+ independent fresh-P6 production/restart
+ V5/V6 reject-before-reuse
+ truthful current docs/config/public surface
+ stage-local and final affected regression/integration closure
```

Only an independently reviewed revision-8 P6 PASS opens the P7 implementation gate. P7 completion then opens the separate post-P7 storage/I-O reset gate.