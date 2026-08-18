# mdstats 0.20.80a0 — complete legacy schema compatibility

## Failure fixed

A campaign created before 0.20.77a0 could pass the top-level
`training_campaign` migration and then fail while loading its nested production
materialization plan with:

```text
TrainingDataSerializationError: Feature-metric policy digest mismatch.
```

The older feature-metric policy did not serialize
`randomized_projection_seed`; similarly, the older partition policy did not
serialize `cross_validation_seed`.  Current constructors supplied deterministic
defaults, but then recomputed the digest from the newer field set.  The record
was valid and unchanged; its reconstructed current-schema digest was different.

## Compatibility audit

The complete source history available for the campaign implementation,
0.20.63a0 through 0.20.79a0, was compared at the serialized dataclass field,
`_payload()`, schema, parser-version, and parent-digest levels.  The supported
legacy identities are:

| Record family | Historical identity | Current identity | Migration |
|---|---|---|---|
| Feature metric policy | field set without `randomized_projection_seed` | same schema plus explicit seed | use runtime seed `0`, preserve exact legacy serialized identity |
| DATA5 partition policy | field set without `cross_validation_seed` | same schema plus explicit seed | use runtime seed `104729`, preserve exact legacy serialized identity |
| Training execution policy | `mdstats.training-execution-policy.v1` | `v2` | use legacy runtime layout and preserve v1 serialization |
| Training campaign policy | `v1`/`v2` | `v3` | verify legacy policy and parent plan, then canonicalize once |
| Production materialization plan | `v2` | `v3` | retain the v2 plan identity and empty historical cross-validation-plan field |
| DATA7 parser | `0.20.35a0`, `0.20.63a0` | `0.20.64a0` | read and preserve the historical parser identity |
| DATA8 parser | `0.20.39a0` | `0.20.66a0` | read and preserve the historical parser identity |

Nested parent records—including DATA5 bundles, production materialization
plans/checkpoints/records, DATA7 archives, DATA8 bundles, and training-campaign
plans—therefore retain their original digests after loading.  This prevents a
valid child migration from cascading into false parent digest mismatches.

## Integrity behavior

Backward compatibility does not bypass integrity checks.  For every migrated
record mdstats verifies either the current canonical digest or the digest of the
exact serialized historical payload, with the digest field itself excluded.
Nested policy/run/artifact records continue to be checked independently.
Changing an old field without rebuilding every affected digest is rejected.

## Resume

Install the 0.20.80a0 code and rerun `evaluate`.  Do not rerun `prepare`,
`preflight`, or completed training.  Completed checkpoints and run-local
execution records are unchanged.
