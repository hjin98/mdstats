---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 8
protocol_version: 6.3.0
status: active
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r1_candidate: 815823494c88969944eee8f58a6cf107d97bcc09
current_gate: R3_D3_REVIEW
---

# MLFF `pi_train` restoration — current pointer

## Current lifecycle

```text
R1 D1/D2 reconstruction:     PASS / ACCEPTED / COMPLETE
R2 dependency recovery:      PASS / CLOSED
R3 D3 architecture contract: PREPARED / AWAITING INDEPENDENT D3 REVIEW
D4 product implementation:   BLOCKED UNTIL D3 PASS/ACCEPTANCE
```

Stakeholder ratified the independently reviewed R1 candidate on 2026-09-15.

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

## Active next artifact

`MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF.md`

is the proposed current-architecture contract. It binds the accepted method and recovered performance/storage closure to current preparation/P2/CampaignStore owners and provides the bounded D4 sequence and qualification requirements.

It requires a fresh independent Protocol-6.3 D3 Review/Challenge before D4 code mutation.

## Current implementation state

Product source remains unchanged by the R1/R2 acceptance transition. In particular, current executable target-order policy still uses `candidate_independent_priority.v1` until an accepted D3-guided D4 cutover replaces it.

This is intentional. Do not partially activate the restored selector by changing policy tokens, schemas, prepared generations, or individual modules before D3 acceptance.

At D4 cutover, old `candidate_independent_priority.v1` prepared target-order products are stale/reconstructible under the new semantic policy and must rebuild through existing preparation/currentness ownership. Do not migrate old ranks into the new method and do not add a parallel compatibility selector.

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
- current campaign/prepared-generation store as currentness/adoption owner;
- final production-scale GPU qualification deferred to the final release package.

## Next gate instruction

Perform an independent Protocol-6.3 D3 review of the prepared R3 contract against:

- the accepted scoped D1/D2 papers;
- Revision 5-8 workplan requirements;
- R2 dependency/provenance map;
- current architecture/owners at the active code base.

If genuine D3 blockers exist, amend the R3 contract at the owning architecture layer. If none exist, record D3 PASS/acceptance and authorize D4 implementation. Do not reopen accepted R1 merely for implementation preferences or execution-only tuning.
