---
kind: workplan-stage-status
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
status: candidate-drafted-awaiting-independent-falsification
date: 2026-09-24
candidate: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE.md
---

# TRAIN2 CuEq parity requalification — Stage B status

## Result

Stage A is PASS. The cross-family evidence obligation is closed.

Stage-B protected-consequence analysis found an additional D2 adequacy defect: current TRAIN2 admission compares calculator forward outputs but does not exercise the backend-specific optimizer-consumed gradient. The workplan has therefore been repaired before implementation rather than adding another forward tolerance.

The proposed D2 candidate now:

- source-closes the acceleration-equivalence family by semantic role;
- preserves source/DATA6 FP32/FP64 calculator tolerances;
- replaces FP32 TRAIN2 Rev86 tail/max thresholds with an e3nn-reference-anchored finite-sample stochastic relation;
- covers actual TRAIN2 physical outputs, scalar objective and optimizer-consumed parameter gradients;
- removes descriptors/FPS from TRAIN2 authorization because current TRAIN2 does not consume them;
- requires both starting and non-initial model-state coverage for a full TRAIN2-operator claim;
- preserves exact trained-state CuEq -> portable-e3nn projection semantics;
- makes FP64 TRAIN2 operator coverage explicit without relaxing its forward tolerance;
- separates expensive qualification from routine doctor witnessing.

The candidate is **proposed, not accepted**. No D4 product change is authorized at this stage.

## Next gate

Perform a fresh independent D2 Review of the immutable candidate. Review must attack, at minimum:

1. whether the finite-sample variance functional is identifiable and non-permissive;
2. whether `D^2 <= V_R` and `V_C <= 2 V_R` are independently defensible budgets rather than hidden threshold fitting;
3. whether global plus cell-conditioned bias closes construction/execution-order cancellation;
4. whether gradient canonicalization and branch coverage genuinely represent the MACE TRAIN2 backend-specific operator;
5. whether `S0 + S1` state coverage is sufficient for the claimed model-state domain;
6. whether removing TRAIN2 descriptor/FPS gating is correct protected-consequence reduction;
7. whether FP64 support is handled honestly;
8. whether the source/DATA6 and projection siblings are source-closed without accidental semantic change.

If review changes candidate semantics, produce a new candidate identity before Stage-C evidence. Do not mutate a reviewed candidate in place.
