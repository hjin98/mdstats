---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 9
protocol_version: 6.3.0
status: active
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r1_candidate: 815823494c88969944eee8f58a6cf107d97bcc09
repaired_r3_candidate_commit: c7db32b4c9f2487450ae18d8d9dd5b948905a9ed
r3_rereview_commit: d575feb36f80f1d8e6abe434005237b410830163
canonical_d3_promotion_commit: 3789e11ed9d652aff29cd61dc3158556f27e4644
d4_authorization_commit: bd3b37832ced3bbe28162592ac4630082fb8c881
d4_implementation_commit: af666839188d62d7cd86bbd341c523f49f045840
d4_reviewed_assembled_candidate: c76a53476596137aa34ec47bb68b7d1ab4bfe706
r3_rereview_verdict: PASS
d4_review_verdict: NO-PASS
current_gate: D4_REPAIR_REQUIRED
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
D4 product implementation:   COMPLETE / INDEPENDENT REVIEW NO-PASS
D4 repair:                    REQUIRED / ACTIVE
```

The accepted D1/D2/D3 authority remains current. Independent review of assembled candidate `c76a53476596137aa34ec47bb68b7d1ab4bfe706` found three D4 closure blockers. Revision 9 is the current repair contract. No Serious Challenge is open against the accepted D1/D2/D3 method/architecture chain; the open challenge is bounded to D4 conformance and acceptance evidence.

## Current accepted authority

For the restored target-training-order scope:

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus the reconciled canonical MLFF Architecture Manual chapters and dependency graph
- D4 repair contract: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_9.md`

General MLFF method/architecture authority remains current for unaffected surfaces.

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

Pre-adoption MVSTATE/history/checkpoint state remains subordinate authenticated reconstructible `prepare`/prepared-storage state. It is not CampaignStore currentness and is never a downstream scientific input.

## Blocking D4 repair

1. Remove the unowned REPAIR2 early-exit that suppresses zero-new-coverage proposals before the accepted later objective components and strict `J` gate can be evaluated.
2. Produce representative current-scale complete prepare/order/publication/reload performance/resource evidence required by canonical D3 and Revision 8; the small 32-frame checkpoint is insufficient for that claim.
3. Reconcile the eight known affected architecture/manual/CLI/spec/help static failures to current authority and rerun the closure batch with no unresolved failures. Baseline equality is not final impact closure.

Use reduction/rewiring, not wrappers. Do not create a fallback selector, old/new router, alternate suffix, second currentness/checkpoint store, semantic migration layer, or new cleanup authority.

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

Implement Revision 9 as a bounded D4 repair, record its exact validation/evidence, then perform a fresh independent D4 re-review of the assembled candidate. Close/archive the workplan only after that re-review passes.