# mdstats 0.20.64a0 production-gate correction

This source package corrects the two blockers that were emitted only after the final DATA8 variant reported materialization success.

## Root causes

1. `unresolved_frame_strain` was generated for ordinary fixed-cell runs whose inferred manifest intentionally had no strain reference group. The old DATA3 implementation treated every absent group as unresolved. Fixed-cell runs now use their own selected cell as an exact zero-strain baseline. Explicitly grouped strained runs retain their reviewed reference behavior, and ungrouped variable-cell runs still fail closed.
2. `profile_extension_coverage_not_materialized` was generated because production DATA6 omits large per-atom LTA environment objects, while DATA7 coverage checked only those omitted objects. Coverage now reconstructs exact `lta:<species>:<site_class>` labels from retained compact aggregate features.

## Restart behavior

Run the catalog rebuild once after installing this package:

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml prepare --rebuild-catalog
```

The rebuilt DATA3/DATA5 lineage is compared against the existing DATA6 sweep. If frame records, requested roles, model checkpoint identity, and descriptor policy are unchanged, existing descriptor and prediction sidecars are checksum-verified and rebound to the new lineage without repeating MACE inference. DATA7/DATA8 artifacts are regenerated where their parser identity or lineage changed.

A successful DATA8 line now reads that the artifacts are materialized and the final DATA9A gate is pending, avoiding the earlier implication that the complete production gate had already passed.

## Validation

Focused production-gate/model-sweep tests: 59 passed. Campaign and material-profile regressions: 72 passed, 1 environment-dependent real-corpus test skipped. Python bytecode compilation completed successfully.
