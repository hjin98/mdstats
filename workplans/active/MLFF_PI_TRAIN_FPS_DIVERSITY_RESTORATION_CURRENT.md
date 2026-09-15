---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 8
protocol_version: 6.3.0
status: active
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r1_candidate: 815823494c88969944eee8f58a6cf107d97bcc09
repaired_r3_candidate_commit: c7db32b4c9f2487450ae18d8d9dd5b948905a9ed
r3_rereview_commit: d575feb36f80f1d8e6abe434005237b410830163
canonical_d3_promotion_commit: 3789e11ed9d652aff29cd61dc3158556f27e4644
d4_authorization_commit: bd3b37832ced3bbe28162592ac4630082fb8c881
r3_rereview_verdict: PASS
current_gate: D4_IMPLEMENTATION_AUTHORIZED
d4_authorized: true
---

# MLFF `pi_train` restoration - current pointer

## Current lifecycle

```text
R1 D1/D2 reconstruction:     PASS / ACCEPTED / COMPLETE
R2 dependency recovery:      PASS / CLOSED
R3 first D3 candidate:       NO-PASS / SUPERSEDED
R3 repaired D3 candidate:    PASS / ACCEPTED
Canonical D3 promotion:      PASS / PROMOTED / CURRENT
D4 product implementation:   AUTHORIZED
```

The repaired R3 candidate passed fresh independent Protocol-6.3 review and has been reconciled directly into canonical current D3. The promotion consistency/stale-owner check passed. No Serious Challenge is open against the accepted R1/R2/R3 authority chain.

## Current accepted authority

For the restored target-training-order scope:

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus the reconciled canonical MLFF Architecture Manual chapters and dependency graph

General MLFF method/architecture authority remains current for every unaffected surface.

## Current target-order architecture

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

## D4 implementation authority

D4 implementation may now proceed under:

- accepted scoped D1/D2 target-order method papers;
- closed R2 dependency/provenance map;
- promoted canonical D3 target-order architecture;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF_REPAIRED.md`;
- composed workplan Revisions 5-8.

The first product mutations must preserve the existing current owner boundary and must not partially activate the restored selector. The new policy/schema/currentness cutover becomes current only when the restored path is complete enough to satisfy the accepted prepared-generation publication/currentness contract. Do not add old/new selector routers, hidden UID fallbacks, alternate suffix selectors, or a selector-specific currentness/GC system.

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

## D4 acceptance focus

Implementation review must prove, at minimum, exact full-forward/optimized selector equivalence, shared FEAS/NEIGHBOR construction, canonical-obligation behavior, independent MVQUAL, post-repair reconstruction, complete-order suffix, authenticated restart/currentness, OOC/FD/resource closure, clean package/native equivalence when retained, and representative current-scale performance without weakening D1/D2.

## Next gate

Proceed with bounded D4 implementation against the accepted R3 handoff. After implementation, perform an independent D4 review against the accepted D1/D2/D3 authority and workplan. Final production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.
