---
kind: restoration-current-pointer
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 13
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
current_gate: D4_R13_RESOURCE_AND_HAS_CLOSURE_REQUIRED
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
R12 independent re-review:   NO-PASS / PERFORMANCE CLOSED / RESOURCE+HAS CLOSURE REMAIN
D4 current repair:           REVISION 13 / REQUIRED / ACTIVE
```

The accepted scoped D1/D2/D3 authority remains current. Revision 11 closed the six correctness/ownership blockers. Revision 12 successfully closed the material REPAIR2 execution bottleneck and post-`N_max` restart-cost question without changing D2 semantics or adding persistent repair state.

Revision 13 is the active bounded D4 closure for two remaining issues discovered by independent review of assembled candidate `c6fbe03c92f23a79123031922f338966e9c76c6b`.

## Current accepted authority

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus the reconciled canonical MLFF Architecture Manual chapters and dependency graph
- R11 correctness repair: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_11.md`
- R12 performance closure: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_12.md`
- Current closure contract: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_13.md`
- Current independent-review handoff: `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_REVIEW_REVISION_13_HANDOFF.md`

## Accepted R12 closure — preserve

1. R12 `_StateBatch` exact batched REPAIR2 execution over the existing MVIDX/native-row substrate.
2. D2 §9 frontier/objective/tolerance/rank-inheritance semantics unchanged and bounded bitwise scalar/native equivalence recorded.
3. REPAIR2 current-scale wall approximately 6,156 s -> 99 s; whole fresh prepare approximately 2 h 26 m -> 32 m; R11-correct scientific build identity unchanged.
4. Post-`N_max` REPAIR2 replay approximately 6,610 s -> 100 s and no longer dominates resumed prepare; no new repair persistence owner.
5. Every R11 correctness/ownership closure remains intact.

## Remaining blocking D4 closure

### B13-1 — campaign RAM budget is not routed into target-order preparation

`campaign_target_size_runtime._build_current_target_training_order()` resolves the campaign resource snapshot but passes only the CPU worker count into `prepare_target_training_order()`. It omits `resource_scope`. R12 telemetry therefore reports `StageResourceScope.ram_budget_bytes=None` and `queue_memory_budget_bytes=None`.

R12 also measured only current RSS before COVREF and after COVREF release. The resulting -200 MiB end-minus-start value is not a stage peak and cannot falsify a transient high-memory peak.

Revision 13 requires a direct rewire through the existing `resource_scope` interface and representative measurement of actual in-stage COVREF peak RSS under the finite campaign budget. No new resource manager or policy is authorized.

### B13-2 — HAS record is noncanonical Protocol 6.3

The R12 table uses `applied/rejected/review-required` rather than the exact Protocol 6.3 `pem_basis` + `has` interface with `APPLICABLE/NOT_APPLICABLE/REVIEW_REQUIRED` dispositions and a recoverable accepted PEM publication route.

Revision 13 requires the canonical schema. Accepted `main` remains `e72090e21cec5311ce87745b03603f8783cd15a7`; no basis refresh is currently needed.

## Protected architecture

Preserve one exact `P_train`, one complete `pi_train`, exact nested `T_N`, sole `TargetCoverageReference`, one canonical obligation authority, one shared FEAS1/NEIGHBOR1 construction, MVIDX as representation, MVSEL2/REPAIR2 as the one order owner, independent MVQUAL, `prepare` as sole live-input/build/publication orchestrator, and prepared-generation/CampaignStore as sole completed-generation currentness/adoption owner.

Do not add a fallback selector, alternate suffix, repair compatibility mode, second currentness/checkpoint store, repair-side durable cache, second memory manager, duplicate sparse representation, or new cleanup/GC owner.

Final production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.

## Implementation entry point

Start at:

`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_13.md`

on branch:

`design/mlff-pi-train-fps-diversity-restoration`

Implement only the bounded resource-routing/peak-evidence and HAS-representation closure, record affected final evidence, then request another fresh independent review. Close/archive only after that review passes.
