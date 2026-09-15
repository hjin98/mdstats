---
title: "MLFF post-selection threshold ownership"
artifact_level: "D3 software architecture"
status: "accepted branch authority"
branch: "fix/mlff-cv-competence-threshold-separation"
accepted_date: "2026-09-15"
parents:
  - "docs/methods/mlff_post_selection_threshold_policy.md"
  - "docs/methods/mlff_post_selection_threshold_numerical_policy.md"
---

# Post-selection threshold ownership — D3 authority

## Scope

This file is the current D3 owner, on this branch, for ownership/configuration/currentness of the three configurable foundation post-selection thresholds. It supersedes only conflicting threshold-ownership wording in the broader MLFF training-data architecture; unaffected architecture remains governing.

## Ownership graph

No new threshold subsystem is introduced. Existing role-policy owners remain authoritative:

```text
PostSelectionMethodIdentity
  owns shared foundation method and shared checkpoint constraints
  owns no role target ceiling

CvValidationPolicyIdentity
  owns tau_cv   = CV checkpoint target-force ceiling
  owns theta_cv = held-out acceptance metric + threshold

FinalProductionPolicyIdentity
  owns tau_prod = production checkpoint target-force ceiling
```

The effective `CheckpointAdmissibilityPolicy` for a run remains a derived composition of shared method constraints plus the authenticated role-policy ceiling. It is not a second owner.

## Public configuration mapping

For foundation modes (`naive_fine_tuning`, `multihead_replay`) the architecture exposes exactly one configuration source for each threshold:

```toml
[post_selection.cv]
checkpoint_maximum_target_force_rmse_ev_per_angstrom = 0.045  # tau_cv default
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045                                    # theta_cv default

[acceptance]
maximum_target_force_rmse_ev_per_angstrom = 0.030             # tau_prod default
```

The existing `[acceptance].maximum_target_force_rmse_ev_per_angstrom` remains the production threshold source for foundation campaigns and retains its separately accepted generic/scratch meaning. Do not add a synchronized production alias under `[post_selection.production]` merely for symmetry.

`[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom` is the missing foundation-CV checkpoint-policy knob. It is role-specific and must not be inferred from `acceptance_maximum` because the latter follows the outer metric's dimension.

For foundation modes, omission resolves the defaults above. An explicit value is used as written after ordinary finite/positive validation. Explicitly writing the default is semantically equivalent to omission because identity binds the resolved value, not presentation provenance.

P5 scratch remains separately governed. This change does not create an additional scratch CV checkpoint knob or alter scratch defaults.

## Identity and invalidation

All three resolved values are identity-bearing at their existing role-policy owner:

- changing `tau_cv` changes `CvValidationPolicyIdentity`, CV plan/run identity and dependent CV acceptance; production authorization depending on that acceptance becomes stale;
- changing `theta_cv` changes `CvValidationPolicyIdentity` and the same dependent CV/final authorization surface;
- changing `tau_prod` changes `FinalProductionPolicyIdentity` and production plan/run identity only;
- none of these role-only edits changes `PostSelectionMethodIdentity`; and
- a genuinely shared checkpoint constraint still changes shared method identity and both dependent roles.

Current recovery must compare stored method/role-policy ancestry against freshly resolved authority before reuse. Stored metric values are never re-thresholded into current evidence under another configured policy.

## Schema/currentness consequence

The identity objects already carry the role threshold fields. Exposing `tau_cv` through configuration does not by itself require another schema generation: the serialized meaning is unchanged. A non-default configured value naturally changes the existing role-policy content digest. Schema changes are warranted only if representation/meaning changes, not because a value becomes user-configurable.

## D3 -> D4 handoff

D4 must minimally:

1. read optional foundation `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom` with default `0.045`;
2. continue reading `[post_selection.cv].acceptance_maximum` with foundation default `0.045` and outer-metric dimensions;
3. continue reading `[acceptance].maximum_target_force_rmse_ev_per_angstrom` as foundation-production `tau_prod`, default `0.030`;
4. expose all three defaults in generated/example foundation configuration and public documentation;
5. bind the resolved values through the existing CV/final policy identities and run-plan authentication;
6. preserve scratch behavior and all shared replay/physical/integrity gates; and
7. add no alias, wrapper, compatibility translator, duplicate policy store, or new checkpoint engine.
