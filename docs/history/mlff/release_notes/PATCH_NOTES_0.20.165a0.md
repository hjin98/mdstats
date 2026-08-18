# mdstats 0.20.165a0 - TARGET-DATA2B reference-mass coverage authority

This release implements TARGET-DATA2B of the post-0.20.162 target-accuracy and structural-stability roadmap. It freezes the target-development reference and the mathematical meaning of coverage before the deterministic seven-rung target-size ladder is created. TARGET-DATA2C and the later training funnel are not implemented in this release.

## Immutable reference-side coverage authority

A new `TargetCoverageReference` is derived only from the TARGET-DATA2A size-development domains and is bound to DATA4, DATA5, DATA6, TARGET-DATA2A, and FOUNDATION-AUDIT1 digests. The authority persists:

- the frozen development-frame domain for every label domain;
- correlation-unit-balanced empirical reference weights;
- applicable species/group-resolved local-environment distribution families from DATA6;
- pair-specific DATA4 geometry and coordination families;
- target-label force/tail and applicable scalar physical channels;
- cached global and per-species foundation-residual families;
- leave-one-out local reference radii at frozen `beta = 1/128`;
- robust Q01/Q99 extent channels for declared scalar/physical families;
- mandatory DATA5 condition support and detected DATA6 structural-event strata;
- generic material-profile scalar coverage families plus provider-declared environment-class support strata; and
- scalar normalized first-Wasserstein distribution-fidelity diagnostics, explicitly separated from coverage.

The production DATA6 structural representation is intentionally compact: species/group-resolved distributions of atomic local features are retained as per-frame mean, width, extrema, and robust quantile coordinates. TARGET-DATA2B treats each applicable group/family distribution independently rather than using one global whole-frame embedding. Declared material profiles are consumed through the generic `ProfileFeatureCatalog` adapter only: each non-constant valid profile scalar receives independent coverage authority and each provider-declared environment class receives a mandatory support stratum. This preserves LTA site-class evidence without hard-coding LTA logic in the generic coverage module.

## Reference-side empirical-mass scorer

`score_target_subset_coverage()` counts covered mass over the immutable reference, never over the selected subset. A reference element is covered only when a selected representative lies within its frozen leave-one-out local radius. Every required materialized family independently requires at least 95% covered reference mass; extent and mandatory-stratum rules remain separate hard gates.

The local-radius implementation uses an exact weighted nearest-neighbor ordering from `scipy.spatial.cKDTree`, accumulates the normalized leave-one-out reference mass explicitly, and expands the neighbor query only when required by nonuniform correlation-aware weights. It therefore avoids a dense `N x N` distance matrix while preserving the specified weighted radius exactly.

`assert_nested_coverage_monotonicity()` provides a fail-closed audit for later TARGET-DATA2C nested rungs. The scorer also rejects selected frames outside the frozen training-eligible development domain.

## Campaign integration and restart

`target_coverage_reference` is now part of the prepare restart receipt and the prepare contract is bound to `TARGET_COVERAGE_VERSION`. New preparation materializes or deterministically reuses this authority after FOUNDATION-AUDIT1. Preflight and training authenticate the frozen record before proceeding so stale DATA4/DATA5/DATA6, role-freeze, or foundation-audit lineage cannot be consumed silently.

## Gate boundary

This release does **not** create the 128/256/512/1024/2048/4096/8192 subsets. TARGET-DATA2C remains the owner of deterministic ranked selection and exact nested prefix membership. TARGET-DATA2D remains the owner of the 95%-coverage rung screening and the bounded 7 -> <=4 -> 2 -> 1 training funnel.

## Qualification

Adversarial tests cover the two-extrema failure case, center-clustered range failure, full-reference identity, correlation-unit weighting, exact nested monotonicity, protected-role exclusion, full DATA4/DATA5/DATA6/FOUNDATION-AUDIT1 integration, stale-lineage rejection, campaign persistence/reuse, and public/manual contract checks. Broader regressions include TARGET-DATA2A, FOUNDATION-AUDIT1, DATA5, DATA6 structural selection/specification, and the campaign CLI.
