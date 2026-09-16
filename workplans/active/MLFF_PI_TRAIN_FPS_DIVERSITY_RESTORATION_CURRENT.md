---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 14
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
d4_r12_repair_commit: 9c41f44be32dd0e4f3869e6e48be4e85b9effce9
d4_r12_evidence_candidate: c6fbe03c92f23a79123031922f338966e9c76c6b
d4_r12_independent_rereview_verdict: NO-PASS
d4_r13_repair_commit: d993f25e28f7d0886ef7628c0a39feeb91adaf33
d4_r13_evidence_candidate: a616f8aa54a80ff003abeb1a2c6b0e882055e4a7
d4_r13_independent_rereview_verdict: NO-PASS
d4_r14_repair_commit: PENDING_COMMIT
current_gate: D4_R14_IMPLEMENTED_INDEPENDENT_REREVIEW_REQUIRED
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
R11 independent re-review:   NO-PASS / CORRECTNESS BLOCKERS CLOSED
D4 performance repair:       REVISION 12 / IMPLEMENTED
R12 independent re-review:   NO-PASS / PERFORMANCE CLOSED
D4 resource/HAS repair:      REVISION 13 / IMPLEMENTED
R13 independent re-review:   NO-PASS / R13 INTENDED BLOCKERS CLOSED / FEAS1 RESOURCE GAP REMAINS
D4 resource closure repair:  REVISION 14 / IMPLEMENTED / INDEPENDENT RE-REVIEW REQUIRED
```

The accepted scoped D1/D2/D3 authority remains current. R11 correctness/ownership repairs, R12 exact REPAIR2 performance/restart closure, and R13 campaign resource routing/COVREF peak-memory/canonical-HAS closure are accepted and SHALL remain frozen absent contradictory evidence.

Revision 14 is the active bounded D4 closure for the one remaining resource-architecture defect exposed by the R13 evidence.

## Current accepted authority

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus `60_execution_performance.md` and the reconciled canonical MLFF Architecture Manual
- R11 correctness repair: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_11.md`
- R12 performance closure: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_12.md`
- R13 resource/HAS closure: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_13.md`
- Current closure contract: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_14.md`
- Current independent-review handoff: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_REVIEW_REVISION_14_HANDOFF.md`

## Accepted R13 closure — preserve

1. The campaign `_performance_resources(cfg)` snapshot now supplies one root target-order `StageResourceScope`.
2. COVREF, MVIDX, REPAIR2 and MVQUAL receive the finite campaign RAM/CPU budget through existing interfaces.
3. Representative COVREF peak RSS was directly sampled under the finite budget and remained far inside the envelope.
4. The final scientific build identity remains `b8d75b6a1857`, with the accepted 49-swap REPAIR2 trace and unchanged MVQUAL result.
5. The session-local HAS is in the canonical Protocol 6.3 `pem_basis` + `has` schema against unchanged accepted `main` `e72090e21cec5311ce87745b03603f8783cd15a7`.

## Revision 14 closure — implemented, awaiting independent re-review

B14-1 is closed by rewiring, not by addition:

1. `target_order/preparation.py::_build()` derives one FEAS1/NEIGHBOR1 child `StageResourceScope` from the existing root target-order scope — exact root CPU available/budget and RAM budget, existing FEAS widths (`python_workers=workers`, `tree_workers=1`, `blas_threads=1`, `native_openmp_threads=1`) — and passes it through the already-existing `build_target_coverage_geometry(..., resource_scope=...)` parameter.
2. `target_order/feasibility.py` deletes the conditional `manage_resource_scope=resource_scope is not None`; the queue's existing default applies. The flag now has no reader anywhere in the repository.
3. The FEAS1 `status=complete` line carries the stage scope and queue disposition in the shape COVREF already publishes, so the stage budget and admission behavior are observable at representative scale.

No class, function, module or configuration key was added; no resource manager, selector, repair algorithm, persistence/currentness owner, cleanup owner or compatibility path exists.

Representative LTA evidence: FEAS1 inherits `ram_budget=41,804,365,824` B, runs `python=28; tree=1; blas=1; openmp=1`, peaks at 32.91 GiB against a 38.93 GiB budget with zero memory backpressure, takes 528.7 s (R13: 544.6 s), and the published build remains `b8d75b6a1857` with 49 REPAIR2 swaps, Phase A at 361 and MVQUAL {512…16384}. Affected regression: 1,275 passed / 4 failed, all four reproduced at the basis with the change stashed.

Evidence: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R14_D4_CLOSURE_EVIDENCE.md`.

## Protected architecture

Preserve one exact `P_train`, one complete `pi_train`, exact nested `T_N`, sole TargetCoverageReference, canonical obligations, one shared FEAS1/NEIGHBOR1 construction, MVIDX as representation, MVSEL2/REPAIR2 as the one order owner, independent MVQUAL, prepare-owned construction/publication, and prepared-generation/CampaignStore completed-currentness ownership.

Do not add a fallback selector, alternate suffix, repair compatibility mode, second currentness/checkpoint store, repair-side durable cache, second memory manager, duplicate sparse representation, or new cleanup/GC owner.

Final production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.

## Implementation entry point

Start at:

`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_14.md`

on branch:

`design/mlff-pi-train-fps-diversity-restoration`

The bounded FEAS1/NEIGHBOR1 resource-scope closure is implemented and its representative and affected-regression evidence recorded. A fresh independent review against the Revision 14 nine-condition gate is now required. Close/archive only after that review passes.
