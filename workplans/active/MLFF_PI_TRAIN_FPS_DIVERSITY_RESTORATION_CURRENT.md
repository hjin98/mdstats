---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 12
protocol_version: 6.3.0
status: active
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r1_candidate: 815823494c88969944eee8f58a6cf107d97bcc09
repaired_r3_candidate_commit: c7db32b4c9f2487450ae18d8d9dd5b948905a9ed
r3_rereview_commit: d575feb36f80f1d8e6abe434005237b410830163
canonical_d3_promotion_commit: 3789e11ed9d652aff29cd61dc3158556f27e4644
d4_authorization_commit: bd3b37832ced3bbe28162592ac4630082fb8c881
d4_implementation_commit: af666839188d62d7cd86bbd341c523f49f045840
d4_r11_repair_commit: dd96ede2b24540977ee0bb280764907ea258e356
d4_r11_evidence_candidate: 029b274474c1adc3b4ea0021a82abf6a5de8c27d
d4_r11_independent_rereview_verdict: NO-PASS
current_gate: D4_R12_PERFORMANCE_AND_EVIDENCE_REPAIR_REQUIRED
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
D4 correctness repair:       REVISION 11 / IMPLEMENTED
R11 independent re-review:   NO-PASS / CORRECTNESS BLOCKERS CLOSED / PERFORMANCE-EVIDENCE BLOCKERS REMAIN
D4 current repair:           REVISION 12 / REQUIRED / ACTIVE
```

The accepted scoped D1/D2/D3 authority remains current. Revision 11 successfully repaired the six prior correctness/ownership blockers. Fresh independent assembled-candidate review of `029b274474c1adc3b4ea0021a82abf6a5de8c27d` found no basis to reopen those repairs or upstream scientific/numerical authority.

Revision 12 is now the active implementation entry point for the remaining D4 current-envelope closure.

## Current accepted authority

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus the reconciled canonical MLFF Architecture Manual chapters and dependency graph
- R11 correctness/ownership repair contract: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_11.md`
- Current D4 closure contract: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_12.md`
- Independent review handoff: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_REVIEW_REVISION_12_HANDOFF.md`

## R11 surfaces now accepted as repaired

Preserve without redesign unless contradictory evidence appears:

1. D2-correct REPAIR2 frontier/objective semantics and v1 build-identity invalidation.
2. Immutable target-order create-or-verify publication with fail-closed corruption handling.
3. Per-build single-flight `prepare` and same-build checkpoint mutation isolation.
4. Frozen universal structural-family completeness and fail-closed missing-family behavior.
5. Scoped/general D1/D2 documentation reconciliation and the targeted static closure batch.
6. Prepared-generation/currentness ownership and downstream no-scientific-rebuild routing.

## Remaining blocking D4 closure

Revision 12 owns four bounded surfaces:

1. **REPAIR2 execution serialization.** The corrected stage consumes about 6,156 s / 74% of representative target-order wall time while its Python-thread proposal path uses about 1.6 CPU cores. Remove that avoidable execution bottleneck without changing D2 semantics.
2. **Restart cost.** A post-`N_max` restart replays approximately 6,610 s of REPAIR2 before reaching the authenticated suffix checkpoint. Optimize the existing evaluator first; add no new durable repair state unless an explicit D3 Challenge later proves topology change necessary.
3. **RAM-budget evidence.** Resolve whether the reported 36.4 GiB process peak versus 34.5 GiB resource budget is a real stage-budget violation or an invalid total-RSS comparison; repair through the existing resource owner only if a violation is proven.
4. **Protocol 6.3 PEM/HAS closure.** Record the session-local Historical Applicability Set against accepted `main` basis `e72090e21cec5311ce87745b03603f8783cd15a7` and the accepted-base PEM carried there.

## Protected architecture

Preserve one exact `P_train`, one complete `pi_train`, exact nested `T_N`, sole `TargetCoverageReference`, one canonical obligation authority, one shared FEAS1/NEIGHBOR1 construction, MVIDX as representation, MVSEL2/REPAIR2 as the one order owner, independent MVQUAL, `prepare` as sole live-input/build/publication orchestrator, and prepared-generation/CampaignStore as sole completed-generation currentness/adoption owner.

Do not create a fallback selector, alternate suffix, REPAIR2 compatibility mode, second currentness/checkpoint store, repair-side durable cache authority, duplicate sparse representation, or new cleanup/GC owner merely to hide performance cost.

Final production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.

## Implementation entry point

Start at:

`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_12.md`

on branch:

`design/mlff-pi-train-fps-diversity-restoration`

Implement the bounded Revision-12 D4 closure, record paired representative evidence, then request another fresh independent assembled-candidate review. Close/archive only after that review passes.
