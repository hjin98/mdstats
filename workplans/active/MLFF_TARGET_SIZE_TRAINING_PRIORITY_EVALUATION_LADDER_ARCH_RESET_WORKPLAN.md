---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
status: superseded
superseded_by: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V2
---

# Superseded

This V1/review-1 workplan is superseded by:

`MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN_V2.md`

V2 corrects material design errors in V1: cross-validation now occurs only after `select-target-size` freezes `N_selected` and `T_selected`; CV no longer participates in target-size materializability/MVQUAL; fold training subsets are not required to contain `N_selected`; the target-size capacity contract is `Nmax + M3`; and LabelDomain count does not automatically multiply target-size data or evaluation requirements.

Git history preserves the complete V1 text for audit/history. Current implementation must follow V2.
