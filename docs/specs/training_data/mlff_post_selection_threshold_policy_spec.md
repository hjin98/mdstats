---
title: "MLFF post-selection configurable threshold specification"
artifact_level: "D4 normative specification"
status: "accepted branch specification; implementation reconciliation required"
branch: "fix/mlff-cv-competence-threshold-separation"
accepted_date: "2026-09-15"
parents:
  - "docs/methods/mlff_post_selection_threshold_policy.md"
  - "docs/methods/mlff_post_selection_threshold_numerical_policy.md"
  - "docs/arch_manuals/mlff_training_data/85_post_selection_threshold_policy_ownership.md"
---

# MLFF post-selection configurable threshold specification

## Authority and scope

This specification is the current D4 contract, on this branch, for configuration and realization of the three foundation post-selection thresholds. It supersedes only conflicting threshold-resolution wording in `mlff_post_selection_p5_spec.md`, `mlff_data9b3_campaign_cli_spec.md`, the generated configuration contract and associated guide text. All unaffected D4 requirements remain current.

## Configuration contract

For foundation adaptation the following three policy values are independently configurable:

```toml
[post_selection.cv]
checkpoint_maximum_target_force_rmse_ev_per_angstrom = 0.045
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045

[acceptance]
maximum_target_force_rmse_ev_per_angstrom = 0.030
```

Resolution is:

| Semantic value | Configuration owner | Foundation default |
|---|---|---:|
| CV checkpoint competence `tau_cv` | `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom` | `0.045 eV/angstrom` |
| CV held-out threshold `theta_cv` | `[post_selection.cv].acceptance_maximum` | `0.045` in units of `acceptance_metric` |
| Production checkpoint quality `tau_prod` | `[acceptance].maximum_target_force_rmse_ev_per_angstrom` | `0.030 eV/angstrom` |

The CV checkpoint field is valid for foundation modes and is not a second outer-acceptance threshold. It always has target-force RMSE units. A foundation configuration that omits it resolves `0.045`; an explicit finite positive value overrides that default.

`acceptance_maximum` retains its existing metric-dependent semantics. An explicit value is used as written. It never supplies `tau_cv` or `tau_prod`.

The existing `[acceptance]` target-force field remains the foundation-production checkpoint threshold source. Do not add a second production alias merely for symmetry.

P5 scratch keeps its separately accepted resolution and defaults; this specification does not add a new scratch checkpoint field.

## Identity and runtime requirements

The resolved `tau_cv` and `theta_cv` SHALL be serialized by the existing `CvValidationPolicyIdentity`. The resolved `tau_prod` SHALL be serialized by the existing `FinalProductionPolicyIdentity`. `PostSelectionMethodIdentity` SHALL contain none of the three role-only thresholds.

Before CV or production preparation/training and before checkpoint assessment, runtime SHALL authenticate the current method and exact role-policy digest. Checkpoint admissibility SHALL then be composed from the authenticated role ceiling plus shared method constraints through the existing owner.

Changing one threshold SHALL move only its owning role-policy lineage and material dependents:

```text
tau_cv or theta_cv edit -> CV policy/plan/run + CV acceptance; dependent production authorization stale
tau_prod edit           -> final-production policy/plan/run only
shared constraint edit  -> shared method + both roles
```

Existing completed metric records SHALL NOT be reclassified as current evidence merely by applying a newly configured threshold.

## Generated/example/public documentation

Current generated and shipped foundation configuration SHALL show all three defaults explicitly so the operator can discover that each is configurable:

```toml
[post_selection.cv]
checkpoint_maximum_target_force_rmse_ev_per_angstrom = 0.045
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045

[acceptance]
maximum_target_force_rmse_ev_per_angstrom = 0.030
```

The CLI specification and user guide SHALL explain that the first and third values are target-force checkpoint ceilings while `acceptance_maximum` follows the outer metric's units.

Existing explicit configuration values are never silently rewritten. Omission uses defaults. Explicitly specifying a default value and omitting it SHALL resolve the same policy identity when every other field is identical.

## Required executable acceptance

At minimum demonstrate:

1. default foundation resolution is `0.045 / 0.045 / 0.030`;
2. explicit non-default `tau_cv` changes CV policy identity, is honored by checkpoint assessment, leaves shared method and production policy unchanged, and stales dependent CV authorization;
3. explicit non-default `theta_cv` changes CV policy identity/held-out verdict without changing checkpoint target-force units;
4. explicit non-default `tau_prod` changes production policy/run position, is honored by checkpoint assessment, and leaves shared method/current applicable CV acceptance unchanged;
5. equality and next-representable-above boundary behavior apply to each resolved target-force checkpoint threshold;
6. alternate outer metrics cannot donate their threshold to `tau_cv`;
7. generated template, shipped example, CLI spec and guide expose the same three defaults;
8. scratch behavior remains unchanged; and
9. no second production key, threshold registry, checkpoint engine, generic P5 protocol identity, or EVAL2 policy wrapper is introduced.

GPU/production-scale qualification remains deferred to the final complete-release package under standing project policy.
