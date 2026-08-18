# MLFF campaign serialization compatibility

This document defines the backward-reading contract for persisted MLFF campaign
state.  It applies to source releases 0.20.63a0–0.20.82a0 and the historical
DATA7/DATA8 parser identities embedded in those releases.

## Rule

A reader may add deterministic runtime defaults, but it must not silently
replace the serialization identity of a historical child record while its
parent still binds the historical digest.  A legacy object therefore has two
views:

1. **Runtime view:** current Python attributes, including deterministic defaults
   for fields absent from the old payload.
2. **Serialization view:** the exact old schema/parser and field set, used to
   reproduce the stored digest and keep all parent identities valid.

Canonical rewriting is permitted only at an explicit migration boundary whose
parent is also rewritten and committed atomically.

## Compatibility matrix

| Family | Accepted historical forms | Runtime defaults / handling |
|---|---|---|
| `FeatureMetricPolicyTemplate` | pre-seed field set | `randomized_projection_seed = 0` |
| `PartitionPolicy` | pre-cross-validation-seed field set | `cross_validation_seed = 104729` |
| `TrainingExecutionPolicy` | v1 | `runtime_layout_version = legacy-run-cwd.v1` |
| `TrainingCampaignPolicy` | v1, v2 | derive current variant matrix from legacy global method/seed/fold contract |
| `ProductionMaterializationPlan` | v2 | no serialized `cross_validation_plans` |
| `FittedFeatureMetric` / DATA7 bundle | parser 0.20.35a0, 0.20.63a0, 0.20.64a0 | preserve loaded parser version |
| DATA8 bundle | parser 0.20.39a0, 0.20.66a0 | preserve loaded parser version |

## Fail-closed requirements

- The stored digest must match either the current canonical payload or the exact
  historical serialized payload.
- Every nested object is verified independently before its parent is accepted.
- Unsupported schemas and parser versions remain errors.
- Legacy DATA8 may be read for completed-model evaluation.  A new training
  launch still follows current runtime/input validation and may require current
  DATA8 materialization if its old job contract is not launch-compatible.
- Missing or modified checkpoint/model bytes are never repaired by schema
  migration.

## Regression fixtures

The test suite includes actual DATA5 and production-materialization payloads
emitted by 0.20.76a0.  They must load under current code, preserve their original
digests, and serialize byte-for-structure identically.  Separate tamper tests
modify a nested old policy and require rejection unless all affected identities
are deliberately rebuilt.
