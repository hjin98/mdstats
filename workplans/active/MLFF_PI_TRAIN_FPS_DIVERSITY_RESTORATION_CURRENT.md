---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 11
protocol_version: 6.3.0
status: active
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r1_candidate: 815823494c88969944eee8f58a6cf107d97bcc09
repaired_r3_candidate_commit: c7db32b4c9f2487450ae18d8d9dd5b948905a9ed
r3_rereview_commit: d575feb36f80f1d8e6abe434005237b410830163
canonical_d3_promotion_commit: 3789e11ed9d652aff29cd61dc3158556f27e4644
d4_authorization_commit: bd3b37832ced3bbe28162592ac4630082fb8c881
d4_implementation_commit: af666839188d62d7cd86bbd341c523f49f045840
d4_r11_repair_commit: dd96ede2
d4_reviewed_assembled_candidate: c76a53476596137aa34ec47bb68b7d1ab4bfe706
integration_audit_commit: 7a0cb21aaa368ac45b41af98e5df9d8e512e4c9d
r3_rereview_verdict: PASS
d4_review_verdict: NO-PASS
current_gate: D4_REPAIR_IMPLEMENTED_AWAITING_INDEPENDENT_REREVIEW
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
D4 integration audit:        NO-PASS / REVISION 10 COMPLETE
D4 repair specification:     REVISION 11 / IMPLEMENTATION READY
D4 repair:                    IMPLEMENTED / AWAITING FRESH INDEPENDENT REVIEW
```

The accepted scoped D1/D2/D3 authority remains current. Revision 11 composes Revisions 9 and 10 and is the implementation entry point for the bounded D4 repair. The open challenge remains D4-only unless new implementation evidence proves a real upstream contradiction.

## Current accepted authority

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus the reconciled canonical MLFF Architecture Manual chapters and dependency graph
- D4 repair contract: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_11.md`
- Review provenance: Revisions 9 and 10

## D4 repair implementation state

Revision 11 was implemented on this branch at commit `dd96ede2`; the evidence record is
`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R11_D4_REPAIR_EVIDENCE.md`.
Nothing here is independent review: the workplan stays **active / D4 NO-PASS** until a
fresh independent assembled-candidate re-review passes Revision 11 section 12.

Two measured items are routed to the reviewer rather than absorbed locally: REPAIR2's
current-scale cost after the R11-E shortcut deletion (1 h 42 m of a 2 h 19 m target-order
build on the representative LTA campaign), and the REPAIR2 replay that a post-`N_max`
restart performs because repair is not checkpointed. Both are performance-design
questions for D3/D4; neither licenses restoring the shortcut.

Revision 11 owns the exact repair instructions. The six blocking surfaces it addressed:

1. REPAIR2 zero-new-coverage early-exit semantic drift, including stale pre-fix build identity invalidation.
2. Missing representative current-scale complete prepare/order/publication/reload performance/resource evidence.
3. Eight affected static/documentation failures plus contradictory current general D1/D2 target-order construction/qualification text.
4. Same-build concurrent `prepare` checkpoint cross-adoption/prune/delete risk.
5. Silent omission of frozen D2-required universal structural families through provider applicability/narrowing.
6. Destructive replacement of corrupt/conflicting completed target-order artifacts despite immutable/protected publication semantics.

Revision 11 further requires one shared lower-layer advisory-lock primitive, strict fail-closed target-order publication, per-build single-flight preparation, frozen-family completeness checks, REPAIR2-v2 cache invalidation, precise documentation delegation, focused real-owner falsification, and representative current-scale qualification.

Use deletion, relocation, and rewiring. Do not create a fallback selector, old/new router, alternate suffix, second currentness/checkpoint store, semantic migration layer, new cleanup authority, or duplicate lock implementation.

## Protected current architecture

Preserve one exact `P_train`, one complete `pi_train`, exact nested `T_N`, sole `TargetCoverageReference`, one canonical obligation authority, one shared FEAS1/NEIGHBOR1 construction, MVIDX as representation, MVSEL2/REPAIR2 as the one order owner, independent MVQUAL, `prepare` as sole live-input/build/publication orchestrator, and prepared-generation/CampaignStore as sole completed-generation currentness/adoption owner. Final production-scale GPU qualification remains deferred to the final release package.

## Implementation entry point

Start at:

`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_11.md`

on branch:

`design/mlff-pi-train-fps-diversity-restoration`

Implement R11-A through R11-H in the specified dependency order, record exact evidence, then request a fresh independent assembled-candidate D4 re-review. Close/archive only after that re-review passes.
