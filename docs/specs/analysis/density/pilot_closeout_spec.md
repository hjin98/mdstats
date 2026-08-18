---
title: "Stage 11E8a Closeout and Regression Closure"
version: "0.20.15a0"
status: "implemented"
---

# Purpose

Stage 11E8a-S0 through S4 complete the mandatory single-source pilot execution.
This closeout stage does not add a new scientific inference. It closes the
engineering boundary exposed by the package-wide review so that the pilot may be
retained as a scientifically partial result without leaving known regression or
test-environment defects.

# Normative boundaries

## Deterministic LD6 research budgets

`MultilevelResearchOptions` is a research profiler contract, not a production
scene-admission contract. Its documented defaults are deterministic:

```text
max_profile_nodes       4,000,000, additionally clamped by active memory
max_phase_evaluations   2,000
max_workspace_bytes     512,000,000, additionally clamped by active memory
```

The default phase count must not vary with host calibration. An explicit lower or
higher positive `max_phase_evaluations` is authoritative for the research run.
Production density preparation remains governed by `FrameworkDynamicsResources`
and `DensityPlanningLimits`.

## Exact explicit-grid Phase-A bounds

When an atomic or framework density channel supplies `grid_shape`, Phase A must use
that exact logical node count. It must not substitute the per-field maximum voxel
allowance. The explicit-grid path is exact and must not fail on a fictitious maximum-sized
mesh. Interval-derived grids retain conservative budget bounds because adaptive
refinement can request a finer grid during Phase B. Sparse and automatic Phase-A
plans likewise remain budget-bounded when no explicit logical shape is available.

## Resource-test isolation

Tests of one hard limit must construct inputs that remain below all earlier hard
limits. Runtime-derived guardrails remain authoritative in production; tests may not
relax them through legacy count arguments. Test fixtures therefore use a sufficiently
large primary memory budget and reduce unrelated Phase-A counts when testing a small
scene-wide peak limit.

## Optional interactive dependencies

Tests whose scientific operation requires `fast-simplification` must skip at module
collection when that optional dependency is absent. Production calls continue to
raise `GraphUnsupportedFeatureError` with the installation instruction.

## Canonical resource names

Diagnostics use the public `max_density_*` names. Compatibility text may include the
backend-local alias, but tests and documentation must assert the public name.

# Acceptance criteria

1. The previously failing multilevel, planning, framework-density, and mesh-
   simplification subset has no failures in a base installation.
2. Explicit `8 x 8 x 8` dense fields record 512 stencil values and do not inherit a
   fictitious per-field maximum mesh bound.
3. Framework edge quadrature overflow is reported before floating realization.
4. Forced sparse-storage overflow reports `max_density_stored_block_values`.
5. Stage 11E8a-S0 through S4 focused tests remain green.
6. A broader bounded regression sweep records any remaining failures separately from
   optional-dependency skips.

# Scientific status

This closeout does not alter the S4 conclusion. The Na-LTA NVE-continuation pilot remains
`scientifically_partial`: occupied basin identities are supported, while PMF
force-density agreement and observed transition paths remain blocked by provenance
and unresolved transition topology.
