---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 5
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 5 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 5 is the current implementation package for closing the destructive retirement/current-generation cutover before the successor downstream-qualification work begins.

## Authoritative supplied artifact set

Read all of the following as one snapshot-complete P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 current-workspace compatibility requirement, except where revision 5 tightens its evidence mechanism.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — independent-review corrections, current-surface/config/docs repairs, reproducible compatibility proof, and corrected P6 closure semantics.

Precedence is revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All other obligations remain binding.

## Scope correction

P6 is now explicitly a **cleanup/cutover functional-closure package**, not final release/product closure.

A P6 PASS means:

```text
retired V5/V6 target-size/current-mixed authorities are removed or isolated reject-only
+ current P1-P5 V7 lifecycle is coherent and restart-authenticatable
+ public/config/docs surfaces accurately expose that lifecycle
+ exact P5A6 current state remains reproducibly compatible
+ affected regression/integration closes
```

A P6 PASS does **not** mean downstream deployment/PES/relaxation/dynamics/calibration/locked qualification has been implemented. That capability is intentionally assigned to successor workplan `CODE-MLFF-TARGET-SIZE-V7-P7` and remains a required parent-product obligation before final release.

Do not implement P7 functionality as a shortcut inside P6. Do not restore the old `SELECT2` / `verify` state machine, old target-size-study/domain lineage, or downstream-evidence-driven fallback selection.

After P6 implementation, independent Software Design review evaluates this composed revision-5 authority. Only after P6 receives cleanup/cutover PASS should P7 implementation begin.
