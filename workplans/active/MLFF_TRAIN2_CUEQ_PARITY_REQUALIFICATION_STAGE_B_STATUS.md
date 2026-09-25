---
kind: workplan-stage-status
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: B
status: candidate-5-author-ready-awaiting-fresh-independent-review
date: 2026-09-24
candidate: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_5.md
candidate_repair_record: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_5_REPAIR.md
candidate4_independent_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R1.md
independent_review_handoff: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_HANDOFF_C5.md
immutable_candidate_commit: be57964c15ed24e30372de407534efd8173d6bc5
immutable_candidate_blob: db0f59e0f9fb81462a18aa6e607ee9deded19c89
stage_C_state: BLOCKED_PENDING_FRESH_D2_REVIEW_AND_RATIFICATION
D3_D4_state: BLOCKED_PENDING_D2_ACCEPTANCE
---

# TRAIN2 CuEq parity requalification — Stage B status

Stage A remains PASS as **method-design evidence only**.

Immutable Candidate 4 `cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9` received fresh independent D2 Review **NO-PASS**. That candidate remains historical and was not mutated.

Candidate 5 is the author-side repair and is frozen at:

`be57964c15ed24e30372de407534efd8173d6bc5`

with canonical blob:

`db0f59e0f9fb81462a18aa6e607ee9deded19c89`.

Candidate 5 repairs the independent Review blockers by:

- governing complete TRAIN2 state, including EMA, optimizer, scheduler/counter, RNG, and backend mutable state;
- observing EMA as a physical function and optimizer state through canonical common-gradient action probes;
- requiring independent anti-common-mode checks for both model-state and optimizer-state transfer;
- replacing TRAIN2 reuse of source-calculator `rtol/atol` with a new prospective precision-scaled physical numerical budget;
- adding a recurrence-horizon paired adaptation and conservative coherent-drift growth guard;
- using fresh-process means for primary stochastic reduction, separate between/within-process variability, cell-local reference comparators, and typed resolution-insufficiency states;
- requiring two independent complete four-cell qualification ensembles with no pooled rescue or rerun-until-pass;
- removing the Huber `0.01` value as a direct catastrophic backend-discrepancy ceiling;
- protecting rare components by a reference-controlled non-dilution guard;
- expanding loader-derived exposure to predeclared first/last/epoch-boundary/scheduler-discontinuity/metadata-extreme/branch windows;
- using full entry/mid/late reference training-state anchors;
- explicitly proposing source/DATA6 and projection/EVAL2 as new D2 sibling relations rather than historical D4 authority;
- identifying EVAL2 as the portable e3nn forward after qualified projection; and
- narrowing current CuEq TRAIN2 support to FP32 only. FP64 CuEq TRAIN2 must fail closed.

Candidate 5 is **proposed, not accepted**.

The next valid gate is a genuinely fresh independent Protocol-6.4 D2 Review of the exact immutable candidate commit above.

Stage C must not run before that Review passes and the exact passing candidate receives stakeholder ratification. D3/D4 implementation remains blocked.
