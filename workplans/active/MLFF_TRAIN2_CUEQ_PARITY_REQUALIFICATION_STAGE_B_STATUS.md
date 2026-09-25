---
kind: workplan-stage-status
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
status: candidate-6-author-ready-awaiting-fresh-independent-review
date: 2026-09-25
candidate: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_6.md
candidate_repair_record: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_6_REPAIR.md
candidate5_independent_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R2.md
independent_review_handoff: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_HANDOFF_C6.md
immutable_candidate_commit: f3035317dcea1448c9d6d825c6f2d9f156aaec24
immutable_candidate_blob: f2596ef7bb0f146e6a6ec3b0af44ffcf8b96764a
stage_C_state: BLOCKED_PENDING_FRESH_D2_REVIEW_AND_RATIFICATION
D3_D4_state: BLOCKED_PENDING_D2_ACCEPTANCE
---

# TRAIN2 CuEq parity requalification — Stage B status

Stage A remains PASS as **method-design evidence only**.

Immutable Candidate 5 `6e73fbb7af9b8d46f61cf81113259584ffed8527` / blob `4bfd2451cc1835e82e303cc9a597b69b8f8deda9` received fresh independent D2 Review R2 **NO-PASS** with no SERIOUS CHALLENGE to the accepted D1/D2 parent.

Candidate 5 remains historical and was not mutated.

Candidate 6 is the author-side semantic repair and is frozen at:

`f3035317dcea1448c9d6d825c6f2d9f156aaec24`

with canonical Candidate-6 blob:

`f2596ef7bb0f146e6a6ec3b0af44ffcf8b96764a`.

Candidate 6 repairs Review-R2 blockers by reduction:

- deletes the unsupported `delta*sqrt(u)` TRAIN2 error scale;
- deletes recurrence-timescale/secant future-drift extrapolation;
- deletes entry/mid/late state-class extrapolation;
- deletes finite optimizer-action probes as complete-state authority;
- deletes sampled TRAIN2 windows and executes the complete accepted loader/update horizon;
- replaces five-process/standard-error acceptance with an explicit distribution-free 90%-content / 95%-simultaneous-confidence reference tolerance design using 44 fresh-process reference-self and 44 fresh-process candidate confirmations;
- deletes the three-repeat `M_R+epsilon` rare-component allowance;
- narrows authorization to one exact initial-state/corpus/loader/objective/horizon/runtime/order qualification key;
- forbids mid-run e3nn/CuEq switching;
- removes generic source/DATA6 CuEq authority from this candidate rather than inventing a new source-side threshold;
- retains FP32 as the sole proposed CuEq TRAIN2 dtype and keeps FP64 fail-closed;
- separates completed-state projection into an independent structural transfer oracle plus a separate reference-self evaluator envelope; and
- preserves EVAL2 provider identity as portable e3nn after successful projection.

Candidate 6 is **proposed, not accepted**.

The next valid gate is a genuinely fresh independent Protocol-6.4 D2 Review of the exact immutable candidate commit and blob above.

A Review PASS means only that Candidate 6 is coherent enough to test. Stage C still requires stakeholder ratification of that exact passing candidate. D3/D4 implementation remains blocked.
