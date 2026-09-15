---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 8
protocol_version: 6.3.0
status: active
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r1_candidate: 815823494c88969944eee8f58a6cf107d97bcc09
reviewed_r3_candidate: e24aef905fc09ccfc6c9d148b839bada28310200
repaired_r3_candidate_commit: c7db32b4c9f2487450ae18d8d9dd5b948905a9ed
rereview_handoff_commit: e32b187e4849f555752aefdddd5bee08e458d83a
current_gate: R3_D3_REREVIEW
---

# MLFF `pi_train` restoration - current pointer

## Current lifecycle

```text
R1 D1/D2 reconstruction:     PASS / ACCEPTED / COMPLETE
R2 dependency recovery:      PASS / CLOSED
R3 first D3 candidate:       NO-PASS / SUPERSEDED
R3 repaired D3 candidate:    REPAIRED / AWAITING FRESH INDEPENDENT REREVIEW
Canonical D3 promotion:      BLOCKED UNTIL R3 REREVIEW PASS
D4 product implementation:   BLOCKED UNTIL R3 PASS + CANONICAL D3 PROMOTION
```

## Current accepted method authority

General MLFF authority remains with the existing general method papers. For the restored target-training-order scope the sole accepted owners are:

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`

R1 and R2 remain closed and are not reopened by the R3 repair.

## Active R3 artifacts

Use only the repaired candidate for current R3 design:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF_REPAIRED.md`
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_REREVIEW_HANDOFF.md`
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_REPAIR_STATUS.md`

The first candidate reviewed at `e24aef905fc09ccfc6c9d148b839bada28310200` is historical review provenance only.

## Repaired architecture

The repaired candidate requires one direct current chain:

```text
exact P_train
 -> sole TargetCoverageReference
 -> one canonical membership-obligation authority
 -> one shared exact FEAS1/NEIGHBOR1 construction
      -> FEAS1 support/capacity report
      -> authenticated NEIGHBOR1 store
           -> MVIDX adoption/inversion
                -> MVSEL2
                -> configured REPAIR2
                -> exact repaired-prefix reconstruction
                -> complete TargetTrainingOrder
 -> independent MVQUAL from primitive reference + canonical obligation definitions
 -> current P2 projection
 -> unchanged P3/CV/replay/production
```

Pre-adoption MVSTATE/history/checkpoint state is subordinate reconstructible `prepare`/prepared-storage build state authenticated by prospective build identity and attempt ownership. It is never CampaignStore currentness and is never a downstream input.

## D3 promotion boundary

The repaired candidate is not yet canonical D3. A fresh independent Protocol-6.3 D3 review must PASS it first. Then the exact accepted design must be reconciled directly into the canonical D3 Architecture Manual before product source changes begin.

At minimum promotion covers:

- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`
- `docs/arch_manuals/mlff_training_data/50_target_size_selection.md`
- `docs/arch_manuals/mlff_training_data/60_execution_performance.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`

Do not preserve conflicting current target-order architecture as a permanent amendment overlay.

## Protected current architecture

Preserve:

- one current `U_size -> P_train + M3` split;
- one `P_train` and one complete `pi_train`;
- exact nested `T_N=pi_train[:N]`;
- current configurable target-size ladder and `pi_eval/M1/M2/M3`;
- current P3 training/evaluation/reducer semantics;
- current post-selection CV/replay/production lifecycle;
- `prepare` as sole live-input/build/publication orchestration owner;
- prepared-generation/CampaignStore as sole completed-generation currentness/adoption owner;
- final production-scale GPU qualification deferred to final release.

## Next gate

Perform the fresh independent D3 re-review specified by `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_REREVIEW_HANDOFF.md`.

Do not modify product code, current policy tokens, prepared schemas, or canonical D3 before that review. If the repaired candidate passes, promote canonical D3 first; only then begin D4.
