# mdstats 0.20.163a0 — TARGET-DATA2A lineage-safe target-size authority

This release implements the first gate of the post-0.20.162 target-accuracy and structural-stability roadmap. It does not yet implement the new reference-mass coverage calculation or target-size funnel; it freezes the only evidence domain those later gates are permitted to inspect.

## TARGET-DATA2A role freeze

A new immutable `TargetDataRoleFreeze` is derived from the existing DATA5 partition bundle. DATA5 remains the owner of correlation-aware partition construction; TARGET-DATA2A is the narrower authority consumed by future target-size logic.

For each label domain the freeze records:

- training-eligible development units and frame UIDs;
- outer-monitor/final-validation, uncertainty-calibration, locked-test, purged, and excluded units/frames;
- CV evaluation and checkpoint-monitor units by fold;
- every authorized development trajectory interval; and
- exact DATA5 partition, leakage-audit, source-catalog, and frame-catalog lineage digests.

Future target-size evidence can call `require_size_selection_frames()` or `require_size_selection_units()` and fails closed if protected evidence is supplied.

## Correlation-family hardening

TARGET-DATA2A performs an additional family-level audit not previously owned by DATA5 CV leakage checks:

- exact DATA3 geometry-fingerprint families cannot cross independent outer evidence roles or training/checkpoint-monitor/evaluation roles inside a CV fold;
- authenticated upstream near-duplicate/structural families can be supplied explicitly and receive the same audit;
- explicit source-level correlation-family assertions are supported; and
- active-learning lineage/generation metadata is retained as provenance without treating an entire trajectory lineage as one indivisible duplicate family.

This distinction prevents broad lineage identifiers from making normal trajectory partitioning impossible while preserving a fail-closed hook for genuine near-duplicate families.

## Restart and migration behavior

New `prepare` runs persist `target_data_role_freeze` immediately after DATA5. Existing prepared campaigns can derive and persist the authority from compact DATA2/DATA3/DATA5 records without restoring DATA4 or rerunning DATA6-DATA9A. The role-freeze digest/version is included in the prepare restart receipt contract.

Historical campaign records remain readable; no historical role split is silently rewritten.

## Qualification

Focused tests cover:

- exact development/protected-role authority mapping;
- rejection of protected frames by the size-selection authentication API;
- deterministic digest and serialization round trips;
- fail-closed authenticated near-duplicate families crossing CV evidence roles;
- rejection of family maps containing frames outside DATA5;
- migration without a DATA4 record; and
- prepare-restart contract binding.

The pre-existing DATA5 and campaign-store regression suites are also rerun at this gate.
