---
kind: workplan-review
protocol_version: 6.4.0
status: pass-as-workplan-after-repair
review_date: 2026-09-24
reviewed_workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: 8d7c87ae3130f18b6b1c8f33c632a2483eee9b6b
supersedes: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R1.md
highest_reviewed_domain: D2
authority_acceptance: false
---

# MLFF TRAIN2 CuEq parity requalification — Workplan Review R2

## Disposition

**PASS AS WORKPLAN AFTER REVISION-3 REPAIR.**

R1 repaired the first exhaustive set of plan defects. R2 deliberately re-reviewed the repaired plan and found three additional material obligations that R1 had left conditional. Revision 3 closes them.

## Additional findings closed

### R2-1 — Rev86 is not source-closed accepted D2 authority

The accepted Protocol-6.4 D2 kernel at `a759e81...` exact-imports `a4824d2...` and forbids an unlisted/backend-observed tolerance from creating a new equivalence relation. Direct inspection of that exact source finds no CuEq-specific relation and no FP32 parity rule. The current D4 specification index also classifies backend parity/hotfix/qualification material as non-semantic history.

Revision 3 therefore treats the missing TRAIN2 CuEq parity relation as a **confirmed D2 closure obligation**, not merely a provenance question. Rev86 remains a conservative executable fail-closed guard and historical evidence until the bounded D2 relation is formally accepted.

### R2-2 — Stored realization currentness defect is direct and real

`_stored_training_acceleration_realization(..., require_qualified=True)` checks backend, device/dtype, checkpoint bytes, and the stored `qualified` flag, but not the currently accepted parity-method/policy identity. Revision 3 requires direct repair through the existing policy/parity/realization owners; incidental stage ordering cannot substitute for consequential-use authentication.

### R2-3 — Parity execution and CUEQ-PHASE1 production authorization are not currently the same gate

The repository contains only deferred/pending positive CUEQ-PHASE1 evidence in the located release/audit records, and a search found no later positive qualification artifact. The ordinary campaign runtime does not directly consume `CueqPhase1QualificationRecord`; PERF-CERT1/FINAL-GPU1 do.

Revision 3 therefore requires explicit separation between executing CuEq candidate training to generate qualification evidence and claiming production CuEq authorization. Doctor parity alone cannot upgrade the higher-level gate.

### R2-4 — Selection smoke strength is bounded

The doctor corpus consists of one source structure plus deterministic local variants. The reported realization had three structures/15 atoms. FPS parity uses structure-mean invariant descriptors and `selection_fraction=0.5`, so only two structure IDs are selected. Revision 3 records the `100/100` equality result as a useful local smoke, not generic selection-robustness evidence.

## Final plan-level state

Revision 3 now contains:

- exact accepted-parent pins and candidate-composition semantics;
- a confirmed missing-D2-relation closure path;
- evidence provenance and raw-vs-summary rules;
- finite-sample/inferential statistical alternatives without pseudo-replication;
- order/warm-up/process/quantile/cardinality falsification;
- dimensional/channel/descriptor consequence semantics;
- cheap-smoke versus qualification-corpus separation;
- independent CUEQ-PHASE1/FINAL-GPU1 authorization boundaries;
- direct stale-realization currentness repair;
- realization-to-training-identity impact projection;
- independent oracles, no retry-until-pass, and target-host acceptance;
- bounded D3/D4 simplification requirements with no duplicate registry.

No remaining workplan blocker was found. The numerical method itself remains under Serious Challenge and requires Stage A -> Stage B -> independent D2 Review -> stakeholder ratification before implementation authority exists.
