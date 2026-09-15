---
kind: authority-alignment-and-d3-d4-handoff
protocol_version: 6.3.0
status: active
branch: fix/mlff-cv-competence-threshold-separation
parent_workplan: workplans/active/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_WORKPLAN.md
accepted_baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
highest_open_owner: D3
---

# MLFF configurable 45/45/30 threshold alignment

## Current disposition

D1/D2 threshold policy is now **accepted branch authority** after independent re-review and explicit stakeholder ratification on 2026-09-15. The stakeholder decision is that all three foundation post-selection thresholds are configurable by design, with generated/current defaults `45 / 45 / 30 meV/angstrom`.

This handoff supersedes parent-workplan wording that describes any of those three values as an immutable policy constant. The role separation, evidence interpretation, fixed-budget rule, selective invalidation and no-duplicate-machinery constraints remain unchanged.

## Governing authority

- D1: `docs/methods/mlff_post_selection_threshold_policy.md`
- D2: `docs/methods/mlff_post_selection_threshold_numerical_policy.md`
- D3: `docs/arch_manuals/mlff_training_data/85_post_selection_threshold_policy_ownership.md`
- D4 specification: `docs/specs/training_data/mlff_post_selection_threshold_policy_spec.md`
- independent D1/D2 re-review: `workplans/active/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_D1_D2_REREVIEW.md`

These files own only the threshold-policy delta; unaffected semantics remain with the existing broad D1-D4 owners. Before integration, the broad canonical papers/specifications should be consolidated so they no longer contain contradictory fixed-value wording; do not duplicate authority during that consolidation.

## Exact configuration design

For foundation modes:

```toml
[post_selection.cv]
checkpoint_maximum_target_force_rmse_ev_per_angstrom = 0.045
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045

[acceptance]
maximum_target_force_rmse_ev_per_angstrom = 0.030
```

The first field is the only new public configuration surface required by the stakeholder clarification. Reuse the existing CV policy field and resolver; do not add another threshold object. The existing outer CV field and production `[acceptance]` field remain their current owners.

## D3/D4 repair contract

Current implementation already serializes both role target ceilings in `CvValidationPolicyIdentity` and `FinalProductionPolicyIdentity`. The missing concretization is that foundation CV currently hard-codes `0.045` instead of reading an explicit optional CV checkpoint field.

Repair by alteration of the existing resolver/configuration path:

1. foundation `resolve_cv_validation_policy_identity(...)` reads optional `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom`, default `0.045`;
2. `acceptance_maximum` remains independently configurable/default `0.045` for foundation modes and follows `acceptance_metric` units;
3. production continues to read `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, default `0.030`;
4. generated `init`, `campaign.toml.example`, CLI specification, P5 specification and user guide expose/explain all three values;
5. explicit default and omitted default resolve identical policy identity;
6. a non-default CV checkpoint value changes `CvValidationPolicyIdentity` and dependent CV/final authorization, not shared method or production policy;
7. scratch retains pre-change resolution and the new foundation CV checkpoint field must not silently broaden scratch semantics; and
8. no schema generation, wrapper, alias, registry, compatibility translator, P5 `TrainingProtocolIdentity`, generic EVAL2 plan or second checkpoint engine is introduced solely for this configurability change.

## Required affected regression

At minimum add/adjust tests for:

- foundation defaults `0.045 / 0.045 / 0.030`;
- explicit CV checkpoint threshold below/above default is honored at real checkpoint assessment;
- CV checkpoint-only edit changes CV policy/run identity, stales dependent production authorization and leaves shared method/production policy unchanged;
- CV outer-only edit remains dimensionally separate;
- production-only edit remains production-only;
- equality / `nextafter` boundary behavior uses each resolved value;
- generated and shipped configuration expose all three defaults;
- explicit-default versus omission identity equivalence; and
- scratch unchanged / no hidden global coupling.

Reuse the existing focused threshold-separation test surface and real `cross-validate -> persisted CV acceptance -> train-production` harness. Production-scale GPU qualification remains deferred to final release.

## Closeout

After D4 repair and executable affected regression, perform one assembled implementation review against the accepted parameterized authority. If PASS, consolidate the broad canonical authority documents, refresh semantic history wording from fixed-default to configurable-with-defaults, perform closeout-learning/HAS reconciliation, update the active index, and archive the cycle.
