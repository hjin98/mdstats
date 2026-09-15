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
r3_rereview_verdict: PASS
current_gate: R3_CANONICAL_D3_PROMOTION
---

# MLFF `pi_train` restoration - current pointer

## Current lifecycle

```text
R1 D1/D2 reconstruction:     PASS / ACCEPTED / COMPLETE
R2 dependency recovery:      PASS / CLOSED
R3 first D3 candidate:       NO-PASS / SUPERSEDED
R3 repaired D3 candidate:    PASS / ACCEPTED FOR CANONICAL D3 PROMOTION
Canonical D3 promotion:      REQUIRED BEFORE D4
D4 product implementation:   BLOCKED UNTIL CANONICAL D3 PROMOTION + CONSISTENCY CHECK
```

A fresh independent Protocol-6.3 D3 re-review has passed the repaired R3 candidate. The review did not reopen R1 or R2 and found no Serious Challenge.

## Current accepted method authority

General MLFF authority remains with the existing general method papers. For the restored target-training-order scope the sole accepted owners are:

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`

R1 and R2 remain closed.

## Accepted R3 design candidate

The accepted-for-promotion R3 design is:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF_REPAIRED.md`

Independent PASS record:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_REREVIEW_PASS.md`

The first R3 candidate and its NO-PASS review remain historical provenance only.

## Accepted R3 architecture

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

Pre-adoption MVSTATE/history/checkpoint state is subordinate authenticated reconstructible `prepare`/prepared-storage state. It is not CampaignStore currentness and is never a downstream scientific input.

## Canonical D3 promotion gate

The repaired candidate has passed review but is not yet current canonical D3. Before any D4 product mutation, reconcile the exact accepted design directly into the Architecture Manual and verify that no stale competing target-order architecture remains.

At minimum promotion covers:

- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`
- `docs/arch_manuals/mlff_training_data/50_target_size_selection.md`
- `docs/arch_manuals/mlff_training_data/60_execution_performance.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- any additional current D3 passage found to encode the superseded target-order topology.

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

Promote the accepted R3 architecture into canonical current D3 and run the required internal-consistency/stale-owner check.

Do not modify product code, activate a new target-order policy token, or set `d4_authorized: true` before that promotion closes. After successful promotion verification, D4 implementation may begin under the accepted R3 contract.
