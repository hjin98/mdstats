---
kind: R1-gate-status
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
workplan_revision: 8
gate: R1
protocol_version: 6.3.0
status: INDEPENDENT_REREVIEW_PASS_AWAITING_STAKEHOLDER_RATIFICATION
accepted_current_authority_changed: false
implementation_authorized: false
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_snapshot: 3937881ef00222e80845aa81f5471d89a4a7736c
active_handoff: NONE_REVIEW_COMPLETE
---

# R1 status — independent D1/D2 re-review PASS; stakeholder ratification pending

## Disposition

Independent Protocol-6.3 D1/D2 re-review of the repaired MVSEL2 reconstruction returned **PASS**. No remaining genuinely blocking D1/D2 defect or new Serious Challenge was found in the proposed reconstructed method.

The effective proposed authority surface is now consolidated directly in:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`.

Supporting reconstruction evidence is:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_RECONSTRUCTION_EVIDENCE.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md`.

The former repair addendum and independent-review handoffs are historical evidence only and no longer participate in authority precedence.

## Closed review findings

The reviewed candidate now has one selector-specific fitted owner (`TargetCoverageReference`), one uniform instantiated `0.95` family threshold, exact recovered neighborhood and MVSEL2 numerical semantics, certified-lazy/full-forward equivalence, configured-shell REPAIR2 with exact post-divergence reconstruction, independent MVQUAL, and full-order continuation through all current `P_train`.

Hard-support reconciliation preserves current P2 configuration: scientific support locus is distinct from requirement strength; same-locus obligations with identical current incidence compose to one canonical obligation with `k=max(k_i)`; aliases cannot add hard-gain votes; true same-locus incidence/applicability contradictions fail closed.

## Authority state

**No accepted D1/D2 authority has changed yet.** Accepted-current method papers at `e72090e21cec5311ce87745b03603f8783cd15a7` remain authoritative.

The proposed D1/D2 pair has passed independent review and is now awaiting the designated stakeholder decision. If the stakeholder ratifies the exact pair, the next action is explicit reconciliation/promotion into `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md`, followed by bounded dependent impact closure and R2.

R2/D3/D4 implementation remains blocked until that promotion occurs. Final production GPU qualification remains deferred to the final-release qualification package.

## Current gate

```text
INDEPENDENT_REREVIEW_PASS_AWAITING_STAKEHOLDER_RATIFICATION
```
