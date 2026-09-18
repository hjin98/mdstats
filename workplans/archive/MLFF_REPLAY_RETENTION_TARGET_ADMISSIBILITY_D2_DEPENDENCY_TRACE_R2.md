---
kind: semantic-definition-dependency-trace
protocol_version: 6.4.0
status: PROPOSED_D2_RENEWAL_R2_NONAUTHORITATIVE_TRACE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
parent_D1_ratified_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
accepted_D2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
repaired_from_D2_R1_candidate: e2b39917ab8c16556eb218d6a41e9682331bbca0
repair_basis_D2_R1_review_commit: 786dd6fd40f15a048eb53dcb3c75b39087ed2ce4
d2_candidate_blob: 3e7fb744fc733f23bbd93a8347246cfa306ebe89
scope:
  - docs/methods/mlff_numerical_algorithmic_method.md
---

# D2 replay/target renewal R2 dependency trace

R2 preserves the R1 numerical policy and repairs the three R1 blockers.

## R1 repair closure

1. `D2.DEF.052` now binds exact replay training label payload/reference identity, training provider/prediction semantics, and the training-consumed projection `Q_r^train`; retention measurement uses `Q_r^ret`. TRUE_REFERENCE label/provider changes can no longer be misclassified as assessment-only.
2. `D2.DEF.057` and `D2.DEF.060B` require evaluator/provider numerical semantics to be identical or already established equivalent; literal software provider identity is not D2 authority.
3. `D2.DEF.062` now fail-closes invalid replay thresholds/order/conversion collapse, missing governed checkpoints/assessments, unrecoverable measurement-equivalence cases, and absent current-CV authorization.

## Fresh R2 challenge requirements

Re-review the whole amended D2 surface, with special attention to:

- whether `Q_r^train`/`Q_r^ret` projection by consumption is complete and noncircular;
- whether TRUE_REFERENCE and FOUNDATION_PSEUDO training labels are both bound strongly enough to protect gradient identity;
- whether provider-equivalence language relies only on accepted numerical semantics rather than software names;
- whether the expanded typed failure set closes every new invalid branch without converting recoverable recomputation into unnecessary terminal failure;
- whether all R1-passing replay boundary, role-threshold, strict-order, currentness and reassessment semantics remain unchanged.
