---
title: "Stage 11E-GR0 Common Grid Geometry and Numerical Diagnostics"
author: "mdstats"
date: "2026-07-27"
version: "0.20.23a0"
status: "implemented"
---

# Purpose

Stage 11E-GR0 extracts the backend-neutral numerical contracts that were first
validated through atomic and framework density plotting.  It does not choose a
resource-feasible grid ladder, construct a density field, extract an isosurface,
or apply a browser policy.  Those responsibilities remain with GR1 and later
stages.

The analysis-owned layer provides one common Euclidean interpretation of an
oblique periodic cell for dense, local-sparse, plotting, and Stage 11 scientific
consumers.

# Runtime ownership

```text
mdstats/analysis/density/numerical_errors.py
    DensityNumericalError
    DensityNumericalInputError
    DensityNumericalResourceError
    DensityNumericalSerializationError

mdstats/analysis/density/grid_geometry.py
    DensityGridGeometry
    resolve_density_grid_shape
    density_grid_intervals
    prepare_density_grid_geometry
    density_resolution_ratio

mdstats/analysis/density/diagnostics.py
    PeriodicMeanPolicy
    CellEquivalenceReport
    ReciprocalResolutionDiagnostic
    PeriodicMeanDiagnostic
    PeriodicSpreadDiagnostics
    evaluate_cell_equivalence
    require_equivalent_laboratory_density_cells
    reciprocal_resolution_diagnostic
    periodic_frechet_mean_diagnostic
    periodic_item_spread_diagnostics

mdstats/analysis/density/stencil_diagnostics.py
    PeriodicGaussianStencilMoments
    gaussian_cutoff_radius
    periodic_gaussian_stencil_moments

mdstats/analysis/density/broadening.py
    ArtificialBroadeningDiagnostic
    cic_assignment_covariance
    effective_artificial_broadening
```

The plotting modules retain compatibility imports and translate analysis-domain
input/resource failures into graph-facing exceptions only at the plotting
boundary.

# Cell and grid geometry

Cell vectors are row vectors.  For target Cartesian interval `h`, automatic grid
shape is

$$
N_i = \max\left(4,\left\lceil \|\mathbf a_i\|/h - 10^{-12}\right\rceil\right).
$$

The realized edge intervals are

$$
h_i = \|\mathbf a_i\|/N_i.
$$

No orthogonalization is permitted.  The exact oblique cell matrix, determinant,
metric, grid-step vectors, and requested-versus-realized intervals are retained
by `DensityGridGeometry`.  Explicit grid shapes are validated as three positive
integers and are never silently rescaled.

# Periodic means and spread

The existing deterministic multi-start flat-torus Frechet/Karcher iteration is
the normative implementation.  Its start policy, medoid search, ambiguity test,
valid-reference mask, weighted spread quantile, temporal subsampling, and
metadata schemas remain numerically unchanged.

A periodic mean that is nonconverged or multiply optimal remains a diagnostic
result but cannot become a valid adaptive-resolution reference.

# Reciprocal resolution

The reciprocal diagnostic is derived from the sampling lattice

$$
2\pi\,\mathrm{diag}(N_1,N_2,N_3)H^{-T}.
$$

It records the shortest nonzero reciprocal sampling vector, the deterministic
integer representative, and the associated real-space reciprocal interval.
The search and tie-breaking rules are unchanged from the tested plotting oracle.

# CIC and Gaussian-stencil broadening

For weighted samples, periodic cloud-in-cell assignment contributes a Cartesian
covariance determined by each sample's sub-grid phase.  The canonical discrete
periodized Gaussian stencil contributes its own Cartesian covariance.  The
analysis layer records

```text
C_CIC
C_stencil
C_effective = C_CIC + C_stencil
rms = sqrt(trace(C) / 3)
```

The stencil-moment calculation does not allocate the dense logical stencil.  It
uses deterministic lexicographic periodic-image enumeration, the existing
Gaussian tail tolerance, exact discrete normalization, and the same covariance
accumulation order as the plotting oracle.

# Exception boundary

The common layer raises only analysis-domain exceptions.  It imports no Plotly,
mesh, browser, graph-style, graph-complexity, or HTML policy.  Plotting adapters
translate:

```text
DensityNumericalInputError    -> GraphAdapterError / GraphStyleError
DensityNumericalResourceError -> GraphComplexityError
```

Graph-facing exception names are therefore adapter behavior, not common
scientific numerical types.

# Compatibility contract

The following plotting imports remain available and return the same record types
and serialized metadata as their analysis counterparts:

```text
mdstats.plotting.density_diagnostics
mdstats.plotting.density_broadening
mdstats.plotting.density_kernel.PeriodicGaussianStencilMoments
mdstats.plotting.density_kernel.periodic_gaussian_stencil_moments
mdstats.plotting.atomic_density.resolve_density_grid_shape
mdstats.plotting.atomic_density.density_grid_intervals
```

For valid inputs, numerical arrays, scalar diagnostics, tuple ordering, schema
versions, and metadata dictionaries must be exactly equal or bitwise equal where
the previous implementation was deterministic.

# Out of scope

GR0 does not own:

- resource-derived target-shape or finest-feasible planning;
- nested-grid ladders or convergence certificates;
- dense/local-sparse backend selection;
- density deposition, convolution, or field normalization;
- marching cubes, mesh repair, Plotly traces, browser admission, or HTML output;
- scientific promotion of a budget-limited grid.

GR1 planning is implemented in `0.20.24a0`, GR2 plotting adaptation in `0.20.25a0`, and GR3 fixed-kernel scientific refinement in `0.20.26a0`; cross-fitted freezing and later field-ownership migration remain GR4--GR5 responsibilities.

# Acceptance tests

The permanent GR0 boundary covers:

- orthogonal and strongly triclinic automatic and explicit grids;
- exact requested/realized interval serialization;
- analysis-versus-plotting class identity and metadata parity;
- periodic translation invariance of Frechet means and spreads;
- reciprocal-resolution agreement with exhaustive skew-cell enumeration;
- CIC phase covariance in oblique cells;
- stencil-moment parity with the dense canonical stencil;
- effective covariance additivity and RMS consistency;
- immutable diagnostic arrays and metadata;
- import isolation from Plotly, mesh, browser, and graph policy;
- plotting translation of analysis resource failures;
- existing atomic/framework density regression tests.

# Implementation status

Implemented in `0.20.23a0`. Stage 11E-GR1 is implemented in `0.20.24a0`, Stage 11E-GR2 in `0.20.25a0`, and Stage 11E-GR3 in `0.20.26a0`. Stage 11E-GR4 is the next implementation stage.
