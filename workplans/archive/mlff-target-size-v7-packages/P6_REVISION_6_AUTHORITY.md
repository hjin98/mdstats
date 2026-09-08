---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 6
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 6 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 6 is the current implementation package for closing destructive retirement/current-generation cutover while leaving a clean storage-neutral P1-P5 architecture for P7 and the later storage/I/O reset.

## Authoritative supplied artifact set

Read all of the following as one P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 current-workspace compatibility requirement, except where later revisions tighten its evidence mechanism.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — independent-review corrections, current-surface/config/docs repairs, reproducible compatibility proof, and corrected P6 closure semantics.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral handoff: remove retired storage lifecycle dependencies from current P1-P5 execution, expose clean P3/P5 owner entry points, and conservatively quarantine stale consequential storage semantics pending the post-P7 storage reset.

Precedence is revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All other obligations remain binding.

## Scope

P6 remains a **cleanup/cutover functional-closure package**, not final release/product closure and not the storage-subsystem renewal.

A P6 PASS now additionally means that the current P1-P5 architecture can be understood and reopened without depending on retired STOR-era `evaluate`/`verify`/DATA7-DATA8 lifecycle semantics, and that later storage work has clear owner-level entry points for P3/P5 state.

P6 must not implement the successor storage inventory/policy/lease/archive/I-O architecture, and must not implement P7 qualification capability as a shortcut. The intended order is:

```text
P6 PASS
 -> P7 implementation + PASS
 -> CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
```
