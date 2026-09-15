---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 10
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
D4 integration audit:        NO-PASS / REVISION 10 ACTIVE
D4 repair:                    REQUIRED / ACTIVE
```

The accepted scoped D1/D2/D3 authority remains current. Revision 10 composes Revision 9 and the broader integration/verification audit. The open challenge is bounded to D4 conformance, integration, persistence/concurrency, documentation reconciliation, and acceptance evidence; no upstream scientific/architectural redesign is presently authorized.

## Current accepted authority

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus the reconciled canonical MLFF Architecture Manual chapters and dependency graph
- D4 repair contracts: Revision 9 plus `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_10.md`

## Blocking D4 repair

1. Remove the unowned REPAIR2 zero-new-coverage early exit and falsify later-objective improvements.
2. Produce representative current-scale complete prepare/order/publication/reload performance/resource evidence.
3. Reconcile the eight known static/documentation failures and remove contradictory current general D1/D2 target-order construction/qualification text by delegating to the scoped method owners.
4. Fence same-build pre-adoption checkpoint mutation so concurrent prepares cannot cross-adopt, prune, or delete one another's unfinished continuation state.
5. Enforce the frozen required universal structural-family catalog fail-closed; do not let phase/geometry provider policy silently thin D2-required target-order evidence.
6. Make completed target-order reference/geometry/MVIDX/build publication truly immutable create-or-verify; corrupt/conflicting protected destinations must fail closed rather than be deleted/replaced by `prepare`.

Use deletion, rewiring, and existing persistence/fencing primitives. Do not create a fallback selector, old/new router, alternate suffix, second currentness/checkpoint store, semantic migration layer, new cleanup owner, or duplicate lock implementation.

## Protected current architecture

Preserve one exact `P_train`, one complete `pi_train`, exact nested `T_N`, sole `TargetCoverageReference`, one canonical obligation authority, one shared FEAS1/NEIGHBOR1 construction, MVIDX as representation, MVSEL2/REPAIR2 as the one order owner, independent MVQUAL, `prepare` as sole live-input/build/publication orchestrator, and prepared-generation/CampaignStore as sole completed-generation currentness/adoption owner. Final production-scale GPU qualification remains deferred to the final release package.

## Next gate

Implement Revision 9 + Revision 10 as one bounded D4 repair round. Record focused owner-level evidence and representative current-scale evidence, then perform a fresh independent assembled-candidate D4 re-review. Close/archive only after that re-review passes.
