---
kind: workplan-review
protocol_version: 6.4.0
status: pass-as-workplan-after-repair
review_date: 2026-09-24
reviewed_workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: 272bc2bab5e7b05c7a4ad4b34e51f56d0d50befa
supersedes: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R3.md
highest_reviewed_domain: D2
authority_acceptance: false
---

# MLFF TRAIN2 CuEq parity requalification — Workplan Review R4

## Disposition

**PASS AS WORKPLAN AFTER REVISION-5 REPAIR.**

## Finding R4-1 — The Protocol-6.4 source-closure omission covers the entire current CuEq parity family

The accepted D2 source contains no CuEq-specific relation. R3 correctly made TRAIN2 FP32 a confirmed missing-D2 relation, but still called source/DATA6 and FP64 parity “unaffected authorities.” That was internally inconsistent.

Revision 5 corrects the scope:

- the D2 candidate must source-close current acceleration equivalence by role/dtype;
- source/DATA6 FP32 and FP64 numerical semantics are formalization-only in this cycle unless independent evidence challenges them;
- TRAIN2 FP32 remains the only numerical relation redesigned because it is the relation falsified/challenged by the target-host evidence;
- no TRAIN2 observation may be used to opportunistically widen source/DATA6 or FP64 tolerances.

This is the minimum source-closed repair: one coherent D2 family, no duplicate numerical owner, and no unnecessary redesign of unaffected numeric siblings.

## Retained closure

All R1-R3 repairs remain applicable: accepted authority pinning/composition, historical evidence provenance, statistical dependence/order/warm-up/quantile resolution, probe-domain adequacy, units/descriptor role, direct stored-realization currentness, optimizer/TRAIN2 identity projection, Rev60/current-policy versus CUEQ-PHASE1 claim separation, FINAL-GPU1 binding, independent oracles, target-host evidence, and no retry-until-pass.

No remaining workplan blocker was found. This review accepts only the plan, not any parity threshold or CuEq realization.
