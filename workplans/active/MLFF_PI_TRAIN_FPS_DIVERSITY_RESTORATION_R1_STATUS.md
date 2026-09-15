---
kind: R1-gate-status
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
workplan_revision: 8
gate: R1
protocol_version: 6.3.0
status: PROPOSED_D1_D2_READY_FOR_INDEPENDENT_REVIEW
accepted_current_authority_changed: false
implementation_authorized: false
---

# R1 status — D1/D2 reconstruction complete, independent review pending

## Disposition

The authoring/reconstruction half of R1 is complete.

Produced:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_RECONSTRUCTION_EVIDENCE.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_INDEPENDENT_REVIEW_HANDOFF.md`.

The candidate reconstructs the latest mature multi-view path while adapting only current-incompatible topology:

```text
exact current P_train
 -> selector-relevant fitted evidence
 -> correlation-balanced multi-view TargetCoverageReference
 -> FEAS1
 -> exact NEIGHBOR1/MVIDX1
 -> MVSEL2
 -> configured-shell REPAIR2
 -> independent configured-prefix MVQUAL
 -> one complete current TargetTrainingOrder
```

Historical per-label-domain/fold selector fan-out and fixed-eight target-size authority are not restored. Current `pi_eval/M1/M2/M3`, P3 target-size training/evaluation/reducer, post-selection CV, replay and production remain unchanged.

## Authority state

**No D1/D2 promotion has occurred.**

Accepted-current papers at `e72090e21cec5311ce87745b03603f8783cd15a7` remain authoritative. The R1 amendments are proposals only.

R2 and production code restoration remain blocked until:

1. independent D1/D2 review passes;
2. any review blockers/Serious Challenges are resolved;
3. the stakeholder ratifies the exact proposed D1/D2 method;
4. accepted-current method papers are promoted/reconciled with explicit provenance.

## Principal proposed semantic restoration

The proposed method makes the following previously under-specified target-order properties explicit:

- hard 0.95 correlation-balanced reference-mass coverage for every required multi-view family;
- q01/q99 extent support for extent-bearing channels;
- canonical condition/event/profile/extent/correlation/current-user hard obligations;
- exact two-phase MVSEL2 ranking with `1e-14` contender tolerance;
- configured active-shell REPAIR2 with non-regressing lower prefixes;
- independent MVQUAL membership qualification;
- complete-order continuation to all of `P_train` after the final configured repaired prefix;
- no use of `M3`, candidate outcomes, CV or downstream evidence in membership construction.

## Review state

Independent review has **not yet been performed** in this authoring context. The dedicated handoff intentionally requires a separate reconstruction/challenge rather than self-approving the candidate.

Human ratification is therefore also pending.
