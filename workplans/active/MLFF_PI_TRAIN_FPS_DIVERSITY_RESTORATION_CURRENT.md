---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 8
protocol_version: 6.3.0
status: active
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r1_candidate: 815823494c88969944eee8f58a6cf107d97bcc09
reviewed_r3_candidate: e24aef905fc09ccfc6c9d148b839bada28310200
current_gate: R3_D3_REPAIR
---

# MLFF `pi_train` restoration — current pointer

## Current lifecycle

```text
R1 D1/D2 reconstruction:     PASS / ACCEPTED / COMPLETE
R2 dependency recovery:      PASS / CLOSED
R3 D3 architecture contract: NO-PASS / REOPENED FOR REPAIR
D4 product implementation:   BLOCKED UNTIL REPAIRED D3 PASS + CANONICAL D3 PROMOTION
```

Stakeholder ratified the independently reviewed R1 candidate on 2026-09-15. The first independent R3 D3 review of candidate `e24aef905fc09ccfc6c9d148b839bada28310200` returned **NO-PASS** without reopening accepted D1/D2.

## Current accepted method authority

General MLFF method authority remains:

- `docs/methods/mlff_scientific_method.md`
- `docs/methods/mlff_numerical_algorithmic_method.md`

For the restored target-training-order scope, the sole current owners are:

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`

The scoped papers supersede conflicting old target-order passages in the general papers while leaving all unrelated current method contracts unchanged.

## Governing workplan stack

Revision 8 remains the exact compatible composition of:

1. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_5.md`
2. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_6.md`
3. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_7.md`
4. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_8.md`

R1 reconstruction/review artifacts remain historical provenance/evidence. The current accepted method is not an amendment stack.

## Closed R1/R2 records

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_STATUS.md`
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_RECONSTRUCTED_EVIDENCE.md`
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md`
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R2_DEPENDENCY_PROVENANCE_MAP.md`

The exact reconstruction ledger is evidence only where accepted method papers now own the proposition.

## Active R3 artifacts

Proposed D3 contract:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF.md`

Independent review/reopen:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_REVIEW_REOPEN.md`

The review identified four blocking D3 repairs:

1. restore one shared NEIGHBOR1 construction consumed by FEAS1 and adopted by MVIDX rather than permitting duplicate geometry work;
2. make one canonical membership-obligation authority an explicit parent of FEAS1, MVIDX, MVSEL2/REPAIR2 and independent MVQUAL semantics;
3. define pre-adoption MVSTATE/rank-history/checkpoint ownership and recovery beneath existing prepare/prepared-storage ownership without creating selector currentness;
4. require canonical Architecture Manual promotion immediately after repaired D3 PASS and before any D4 product-code mutation.

The repaired R3 candidate requires a fresh independent Protocol-6.3 D3 re-review. This NO-PASS does not approve its future repair.

## Current implementation state

Product source remains unchanged by the R1/R2 acceptance and R3 review. Current executable target-order policy still uses `candidate_independent_priority.v1` until a future accepted D3-guided D4 cutover replaces it.

Do not partially activate the restored selector by changing policy tokens, schemas, prepared generations, or individual modules while R3 is reopened.

At eventual D4 cutover, old `candidate_independent_priority.v1` prepared target-order products are stale/reconstructible under the new semantic policy and must rebuild through existing preparation/currentness ownership. Do not migrate old ranks into the new method and do not add a parallel compatibility selector.

## Protected current architecture

The restoration must preserve:

- one current `U_size -> P_train + M3` split;
- one training population `P_train`;
- one complete `TargetTrainingOrder` / `pi_train`;
- exact nested `T_N=pi_train[:N]` memberships;
- current configurable target-size ladder;
- current `pi_eval/M1/M2/M3`;
- current P3 training/evaluation/reducer semantics;
- current post-selection CV/replay/production lifecycle;
- `prepare` as live selector-input/build/publication orchestration owner;
- current campaign/prepared-generation store as completed-generation currentness/adoption owner;
- final production-scale GPU qualification deferred to the final release package.

## Next gate instruction

Repair the proposed R3 D3 contract at its owning architecture layer using the exact requirements in `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_REVIEW_REOPEN.md`.

Do not change D1/D2, do not begin D4 implementation, and do not promote the unrepaired R3 into canonical D3.

After repair, perform a fresh independent Protocol-6.3 D3 review. If that review passes, promote the exact accepted design into the canonical D3 Architecture Manual (`mlff_training_data_architecture.md` plus affected chapter owners) before authorizing D4 product mutation.