---
title: "Stage 11E-GR1 Common Budgeted Grid Planning"
subtitle: "Scientific logical-grid decisions, deterministic ladders, field reuse, and backend-second selection"
author: "mdstats"
date: "2026-07-27"
version: "0.20.24a0"
status: "implemented architecture revision 54"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.82in
fontsize: 10pt
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Purpose

Stage 11E-GR1 owns the scientific decision that converts a requested Cartesian
resolution into one periodic logical grid or an exactly nested logical-grid
ladder. The decision is made under a scientific density resource policy and is
completed before dense, local-sparse, or any later execution backend is chosen.

GR1 builds on the Stage 11E-GR0 cell-metric and diagnostic records. It does not
construct density values, alter the fixed kernel, select a visual bandwidth,
extract a mesh, or admit a browser scene.

# Normative separation

The order is mandatory:

```text
physical target interval
    -> logical periodic grid
    -> scientific budget verdict
    -> frozen logical-grid signature
    -> backend feasibility estimates
    -> backend selection
```

A backend cannot repair an infeasible physical target by silently changing the
grid or kernel. Dense and local-sparse candidates for the same field therefore
carry the same logical-grid and fixed-kernel signatures.

Scientific resource limits are accepted through
`ScientificDensityResourcePolicy` or an explicit logical-voxel limit used by
focused compatibility tests. Plotly, mesh, browser, trace, scene, HTML, and
rendering policies are not valid planner inputs.

# Target and finest-feasible planning

`plan_finest_feasible_density_grid` accepts:

```text
display cell
target Cartesian interval
coarsest admissible Cartesian interval
scientific resource policy or explicit logical-voxel limit
optional immutable metadata
```

The target shape is

$$
N_i = \max\left(4,\left\lceil\frac{\|\mathbf a_i\|}{\Delta_{\rm target}}-10^{-12}\right\rceil\right).
$$

When the target shape fits, the selected shape is exactly the target shape and
the status is `target_reached`.

When the target does not fit but the coarsest admissible shape does, the planner
uses the established deterministic 80-step interval bisection to return the
finest automatic shape within the logical-voxel limit. The status is
`budget_limited`, the reason contains
`unresolved_due_to_resolution_budget`, and the result is not promoted as a
scientifically converged resolution.

The legacy adaptive-broadening sentinel `target_interval=0` means “find the
finest grid admitted by the scientific limit.” It is retained only as a
compatibility numerical request. The signed target geometry records that the
original target was unbounded rather than pretending that zero is a physical
Cartesian interval.

If the coarsest admissible shape itself exceeds the limit, planning raises
`DensityNumericalResourceError`; no partial grid is returned.

# `DensityLogicalGridPlan`

The immutable record contains:

```text
target_geometry
selected_geometry
coarsest_geometry
max_logical_voxels
scientific_resource_signature
status
reason_codes
logical_grid_signature
metadata
signature
```

Each geometry retains both the requested interval, when finite, and the realized
Cartesian intervals. The selected logical grid is signed independently of any
backend.

The valid statuses are:

- `target_reached`;
- `budget_limited`;
- `level_limited`, reserved for a bounded nested ladder.

A `budget_limited` plan is valid diagnostic evidence but is not a scientific
resolution certificate.

# Deterministic nested-grid ladder

`plan_deterministic_density_grid_ladder` starts from the grid shape resolved at
the coarsest interval. For integer refinement factor $r\ge 2$, level $k+1$ is
constructed as

$$
\mathbf N_{k+1}=r\mathbf N_k.
$$

The grids are therefore exactly nested in every periodic lattice direction.
For the default factor two, every parent voxel contains exactly $2^3=8$ child
voxels.

The ladder stops when the longest realized Cartesian interval satisfies the
requested finest interval, when the next exact nested level exceeds the
scientific voxel limit, or when `max_levels` is reached. These outcomes are
respectively:

```text
target_reached
budget_limited / unresolved_due_to_resolution_budget
level_limited / unresolved_due_to_ladder_depth
```

A budget-limited record retains the finest feasible level and the first
requested infeasible level. It does not relabel the feasible level as the
requested finest grid.

# `DensityNestedGridLadder`

The immutable ladder contains:

```text
levels
requested_finest_geometry
coarsest_interval
finest_interval
refinement_factor
max_levels
max_logical_voxels
scientific_resource_signature
status
reason_codes
metadata
signature
```

Construction rejects non-nested shapes, mixed display cells, levels above the
scientific limit, inconsistent statuses, and unsupported serialized schemas.

# Logical-grid identity

`density_logical_grid_signature` hashes the cell, logical shape, realized
intervals, and voxel volume. It deliberately excludes storage backend and
rendering policy. Two backend candidates can describe the same scientific field
only when this signature is identical.

# Identical-field reuse

`DensityFieldReuseKey` binds:

```text
field kind
source signature
sample-selection signature
weight signature
fixed-kernel signature
logical-grid signature
normalization signature
```

Its cache key is backend-independent. Operational metadata such as whether a
cache hit came from dense or local-sparse storage does not alter the numerical
field identity.

`require_identical_density_field_reuse` fails closed when any source, sample,
weight, kernel, logical-grid, normalization, or field-kind identity differs.
No partial signature match authorizes reuse.

# Backend-second planning

`DensityBackendCandidatePlan` records one backend estimate bound to a frozen
logical-grid signature and fixed-kernel signature. It contains feasibility,
storage, workspace, work, and explicit infeasibility reasons.

`select_density_backend_after_grid` accepts one `DensityLogicalGridPlan` and
candidate records. It rejects candidates that change the grid or kernel. An
explicit backend request must be feasible. Automatic selection uses a stable
ordering by estimated scientific work, workspace, storage, and backend name.

The resulting `DensityBackendSelectionPlan` retains the logical-grid-plan
signature, logical-grid signature, fixed-kernel signature, all candidate
records, the selected backend, and the deterministic selection reason.

This stage does not replace plotting's established dense/local-sparse policy.
Stage 11E-GR2 adapts atomic and framework plotting to the common GR0/GR1 layer
while preserving visual and browser behavior.

# Serialization and signatures

Every GR1 persistent record is immutable, JSON-serializable, and signed with a
canonical SHA-256 payload. Deserialization recomputes signatures and rejects
payload tampering. Derived cache keys and logical-grid identities are also
verified when serialized.

# Failure behavior

GR1 fails closed for:

- invalid or singular cells;
- negative target intervals or nonpositive coarsest intervals;
- refinement factors below two;
- nonpositive level or resource limits;
- a coarsest grid that exceeds the scientific limit;
- mixed cells inside one plan or ladder;
- non-nested ladder shapes;
- backend candidates that change the frozen grid or kernel;
- field reuse with differing numerical identities;
- infeasible forced backends;
- signature or cache-key tampering;
- rendering-policy objects supplied in place of scientific resource policy.

Budget and level exhaustion are signed unresolved outcomes when at least one
valid logical grid exists. They are not silently promoted.

# Compatibility boundary

The plotting-private `_finest_budgeted_grid_shape` name remains available as a
compatibility adapter. It delegates to GR1 and translates analysis numerical
input/resource failures into `GraphComplexityError`. The selected shape and
budget-limited Boolean remain regression-compatible, including the historical
zero-target sentinel.

No other atomic/framework plotting ownership moves in GR1.

# Acceptance tests

Focused tests cover:

- target-reached planning in a strongly triclinic cell;
- exact requested and realized interval retention;
- budget-limited finest-feasible parity with the plotting oracle;
- zero-target adaptive compatibility;
- coarsest-grid resource failure;
- deterministic exact factor-two nesting;
- budget-limited and level-limited ladders;
- signed JSON replay and tamper rejection;
- backend-independent field cache keys;
- fail-closed source/weight/kernel/grid mismatch;
- physical-resolution-first/backend-second enforcement;
- infeasible forced backend handling;
- absence of rendering and graph-policy imports.

The affected density diagnostics, broadening, atomic-density, and backend
selection regressions must remain unchanged.

# Implementation status

Implemented in `0.20.24a0`. Runtime owner is
`mdstats.analysis.density.planning`; the plotting compatibility boundary remains
in `mdstats.plotting.atomic_density`. Architecture revision 56 retains GR1 as implemented and records GR2 plotting adaptation and GR3 fixed-kernel scientific refinement as complete. Stage 11E-GR4 is the next implementation stage.
