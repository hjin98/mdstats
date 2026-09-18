---
kind: implementation-workplan-final-review-closure
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-FINAL-D4-REVIEW-CLOSURE
parent_workplan: workplans/archive/MLFF_REPLAY_RETENTION_AND_TARGET_ADMISSIBILITY_REWORK_WORKPLAN.md
d3_d4_workplan: workplans/archive/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_D4_IMPLEMENTATION_WORKPLAN.md
protocol_version: 6.4.0
status: closed-pass
review_verdict: pass
implementation_branch: design/mlff-replay-retention-target-admissibility-rework
accepted_d1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
accepted_d2_target: 32508991d472c1c6e4bd8b818b38d0880401845f
accepted_d3_target: de360579686bd6f06eae8a6a5e26b232d7db847e
reviewed_executable_candidate: 042b84b74d0b109dd576b725eafe6359629a55ea
evidence_binding_descendant: 51db5d33723fad862b803b2487ea448cb876ec06
highest_affected_domain: D4 implementation/concretization and evidence/lifecycle closure under unchanged accepted D1-D3 authority
serious_challenge: none
closed_date: 2026-09-18
precedence: This independent Protocol 6.4 closure supersedes ACTIVE, REOPENED, NO-PASS, and PENDING-REVIEW lifecycle states recorded in the archived cycle snapshots. Accepted current product semantics remain owned by the ratified D1/D2 authorities, accepted D3/D4 specification, and conforming executable implementation.
---

# MLFF replay-retention / target-admissibility rework — final D4 Review closure

## 0. Disposition

**PASS / CLOSED.**

Fresh independent D4 Review of executable candidate `042b84b74d0b109dd576b725eafe6359629a55ea`, with evidence/lifecycle-only descendant `51db5d33723fad862b803b2487ea448cb876ec06`, found no remaining blocker and no Serious Challenge to D1, D2, or D3.

The implementation conforms to accepted D3 target `de360579686bd6f06eae8a6a5e26b232d7db847e`. The cycle is complete and its coordination/review artifacts are archived by this closure commit.

## 1. Governing accepted authority

The closed implementation preserves accepted D1 target `d761171f3c86c3c79b87a90cfc02ac324c261b1a`, accepted D2 target `32508991d472c1c6e4bd8b818b38d0880401845f`, and accepted Gate-D D3 target `de360579686bd6f06eae8a6a5e26b232d7db847e`. No final-review finding requires reopening those authorities.

The resulting current behavior retains the ratified foundation-P5 semantics: replay warning `0.050 eV/angstrom` diagnostic-only; replay catastrophic hard limit `0.100 eV/angstrom` with strict exceedance; foundation CV checkpoint / default-force outer / production checkpoint defaults `0.075 / 0.075 / 0.050 eV/angstrom`; complete governed-checkpoint assessment; D2.DEF.059A and D2.DEF.059B strict target-RMSE ordering; fixed-budget TRAIN2 independent of assessment-only policy; exact D2.DEF.060B measurement reuse; and immutable historical assessments.

## 2. Final D4 repair findings

### R1 — held-out EVAL2 publication ordering: CLOSED

Fresh held-out transport remains attempt-local scratch outside the sealed training root. The representative is frozen before held-out serialization. For a newly computed held-out measurement, the existing `PostSelectionEvidenceStore` durably publishes both `EvaluationMeasurementIdentity` and its metric while scratch is still live; cleanup occurs only after those writes succeed.

No second evidence store, registry, pointer family, durable held-out namespace, or publication marker was introduced. Failure injection proves that outer-measurement publication failure produces no fold assessment or current CV acceptance; retry reuses completed TRAIN2 and regenerates only missing measurement work.

### R2 — shared TRAIN2 policy compatibility: CLOSED

The final implementation preserves one canonical hard-limit value while restoring the supported shared API boundary:

- generic/exported `CheckpointAdmissibilityPolicy()` compatibility default remains `0.030 eV/angstrom`;
- `replay_degradation_budget_ev_per_angstrom` remains a constructor/property compatibility alias;
- `TRAIN2_DEFAULT_REPLAY_DEGRADATION_EV_PER_ANGSTROM` remains `0.030`;
- inconsistent simultaneous legacy/current spellings fail closed;
- historical schema v1 retains its historical serialization/reason;
- current foundation-P5 receives its `0.100` hard limit explicitly from the P5 policy owner;
- the independent `0.050` replay-warning policy remains diagnostic-only.

### R3 — immutable candidate, evidence, and lifecycle binding: CLOSED

The last executable/test mutation is immutable commit `042b84b74d0b109dd576b725eafe6359629a55ea`. Commit `51db5d33723fad862b803b2487ea448cb876ec06` is evidence/lifecycle-only and binds exact evidence to that executable candidate.

The previously inconclusive storage-integration realization was replaced by a complete collected-and-executed result.

## 3. Accepted evidence

Exact-SHA evidence for `042b84b74d0b109dd576b725eafe6359629a55ea` includes compile checks and focused static checks passing; 22 generic TRAIN2/EVAL2 policy/specification tests; 11 P5D CV acceptance tests; 16 P5 R6 guards; 19 P5 R7 guards; 56 replay/target policy-identity tests; 9 replay/target real-owner tests; 38 CV no-admissible/recovery tests; 27 production/restart tests; 291 storage-core tests; and the complete 167-test storage-integration suite passing.

The recorded affected suites total **656 passing tests with zero reported failures or skips**. Structural checks also establish training-only current materialization and one P5 post-selection evidence store.

The repository has no configured executable-source CI/status gate or configured mypy/pyright project gate for this candidate; no absent gate is treated as positive evidence.

Production-scale GPU qualification remains intentionally deferred to the final complete-release package under the standing MLFF project policy. This closure neither claims nor requires that deferred qualification.

## 4. Architecture and complexity disposition

The closed implementation preserves the accepted architecture: acyclic pre-fit/training-only `TrainingTrajectoryIdentity`; training-only sealed run roots; assessment-independent measurement identity; held-out labels/transport absent from current training materialization/root; external immutable assessment records with one CampaignStore currentness plane; one post-selection evidence store; authenticated historical reuse without rewriting historical bytes; retained run-activity/storage-publication ordering; and no hard-decision edge from warning evidence.

The repair altered existing owners rather than adding compensating subsystems. No shadow selector, compatibility service, second store, second registry, or duplicate currentness owner was introduced.

The independently rechecked mixed admissible/no-admissible final-production aggregate-publication question was not established as a defect and remains outside this closed cycle.

## 5. Project Engineering Memory closeout

The closeout learning assessment found no admission-threshold basis for a new PEM family, occurrence, notice, or material mutation of an existing family. The repair is consistent with existing project learning, but ordinary repair chronology remains in Git/workplan evidence rather than being promoted into permanent memory.

No PEM mutation is required.

## 6. Final Challenge and reopen conditions

**No Serious Challenge.**

```text
D1: coherent; unchanged
D2: coherent; unchanged
D3: coherent; adequately concretized
D4: conforming
affected evidence: closed
lifecycle/dependency impact: closed
```

Future reopening requires new evidence falsifying a protected current invariant, such as assessment-only edits retraining an equivalent trajectory; held-out evaluation ancestry re-entering current training materialization/root; scratch disappearing before fresh measurement durability; warning evidence acquiring decision authority; wrong resolved P5 replay hard limits; inadmissible checkpoint promotion; inexact measurement reuse; historical-byte rewriting; or duplicate evidence/currentness/storage ownership.

Absent such evidence, this workplan lineage is closed.
