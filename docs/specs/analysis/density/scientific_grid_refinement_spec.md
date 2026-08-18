---
title: "Scientific Density Grid Refinement and Plotting Reuse"
subtitle: "Stage 11E-GR0--GR5 partial-refactor contract"
author: "mdstats"
date: "2026-07-27"
version: "0.20.26a0"
status: "GR0--GR3 implemented; GR4--GR5 planned under architecture revision 56"
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

This specification defines how Stage 11 reuses the mature atomic-density grid
machinery without importing plotting policy into scientific site discovery.

The selected architecture is a **partial refactor**:

- move backend-neutral grid geometry, resolution, broadening, and scientific
  resource planning into `mdstats.analysis.density`;
- preserve current plotting imports through compatibility adapters;
- keep plotting's visual bandwidth/grid coupling and one-grid selection policy;
- add a separate fixed-kernel Stage 11 convergence policy and separate field,
  basin, and transition-corridor certificates.

This is a planning contract. It does not change the existing density values,
public plotting APIs, or the current Stage 11E8a scientific result.

# Reviewed numerical oracle

The existing implementation under `mdstats.plotting` is the regression oracle
for the common numerical layer:

```text
mdstats.plotting.density_contracts
mdstats.plotting.density_diagnostics
mdstats.plotting.density_broadening
mdstats.plotting.atomic_density
```

The Stage 11 scientific comparison layer currently resides in:

```text
mdstats.analysis.density.species
mdstats.analysis.density.attractors
mdstats.analysis.density.pilot_refinement_lineage
```

The oracle already provides tested behavior for oblique-cell grid construction,
realized Cartesian intervals, periodic Frechet means and positional spread,
reciprocal-resolution checks, cloud-in-cell covariance, Gaussian-stencil
broadening, finest-feasible grid search, dense/local-sparse planning, immutable
metadata, and serialization.

# Non-negotiable separation of variables

The scientific kernel covariance, numerical grid spacing, and rendering mesh
tolerance are distinct:

$$
\Sigma_h \neq \Delta \neq \text{mesh tolerance}.
$$

Plotting may use the visual default

$$
\sigma = c\max_i \Delta_i
$$

and may refine both quantities together to avoid artificial visual broadening.
That behavior must not define a scientific grid-convergence test.

For one Stage 11 grid ladder:

$$
\Sigma_h = \text{constant},\qquad
\Delta^{(0)} > \Delta^{(1)} > \Delta^{(2)} > \cdots.
$$

Bandwidth hypotheses are evaluated by the separate bandwidth-lineage policy.
Grid refinement evaluates only the numerical realization of one fixed kernel
hypothesis.

# Ownership model

## Analysis-owned common layer

The target layout is:

```text
mdstats/analysis/density/grid_geometry.py
mdstats/analysis/density/resolution.py
mdstats/analysis/density/broadening.py
mdstats/analysis/density/refinement.py
```

The common layer owns:

- target Cartesian interval to periodic grid shape;
- realized intervals and logical node/voxel counts;
- reciprocal-space resolution diagnostics;
- periodic Frechet means and item-spread diagnostics;
- CIC assignment covariance;
- discrete Gaussian-stencil covariance;
- combined artificial-broadening covariance;
- target-shape and finest-feasible-shape planning;
- deterministic nested-grid ladders;
- physical-resolution-first/backend-second planning;
- scientific budget-limited status;
- immutable resolution records and field-reuse signatures.

The common layer uses density-analysis exceptions and imports no Plotly, mesh,
browser, HTML, or graph-style policy.

## Plotting-owned policy

Plotting retains:

- automatic visual Gaussian selection;
- default Gaussian-to-grid coupling;
- one-grid visual acceptance;
- under-resolution and marching-cubes warnings;
- graph-facing exception translation;
- render metadata;
- mesh, browser, and scene admission.

`AtomicDensityOptions` may remain a compatibility wrapper around the common grid
policy and a plotting-only broadening policy.

Stage 11E-GR2 is implemented in `0.20.25a0` through the signed plotting-owned
`DensityVisualGridAdaptation` record. Atomic and framework field producers bind
resolved visual numerics to GR0 geometry and optional GR1 replay plans while
preserving established fields, metadata, routing, meshes, and admission policy.
This adaptation remains visual evidence and cannot satisfy GR3 convergence.

## Stage 11-owned policy

Stage 11 adds `ScientificGridRefinementPolicy`, which records:

```text
fixed kernel covariance and signature
nominal interval or resolution-ratio target
deterministic refinement factor or interval ladder
minimum and maximum levels
minimum Delta/sigma target
consecutive passing level-pair requirement
scientific resource policy signature
field-resolution tolerances
basin-convergence tolerances
corridor-convergence tolerances
cross-fit partition signature
budget-limited behavior
```

The policy never changes the Gaussian covariance merely because a dense field is
too large. Backend selection follows the logical grid decision.


## Concrete stopping and correspondence policy

`GridConvergenceStoppingPolicy` records the deterministic refinement factor or interval
ladder, the target $\max_i\Delta_i/\sigma_{\min}$, maximum depth, and at least two
consecutive level-pair passes after the minimum physical resolution is reached. Basin
tolerances include count, periodic anchor displacement relative to kernel scale, basin
overlap, integrated probability change, and correspondence ambiguity. Corridor tolerances
include adjacency equality, ridge/corridor overlap, bottleneck displacement, width/density
change, and split/merge ambiguity. Reaching budget or maximum depth before the criterion
passes is unresolved.

`FeatureCorrespondencePolicy` defines weighted periodic anchor distance, basin/corridor
overlap, probability cost, point-versus-ridge admissibility, maximum assignment cost,
ambiguity margin, deterministic tie-breaking, unmatched features, and split/merge records.
The same signed policy is used across grid, bandwidth, bootstrap, and held-out realizations.

## Versioned initial policy presets

The implementation must not hide tolerance choices in code. The initial presets are
serialized records:

```text
stage11_grid_stopping_v1
stage11_feature_correspondence_v1
```

`stage11_grid_stopping_v1` uses factor-two interval refinement, requires the longest
realized Cartesian interval to satisfy $\Delta_{\max}/\sigma_{\min}\le 0.5$, and
requires two consecutive passing level pairs. Basin passes require unchanged accepted
count, maximum anchor motion no greater than $0.10\sigma_{\min}$, matched-basin overlap
at least 0.95, absolute integrated-probability change no greater than 0.02, and no
unresolved correspondence ambiguity. Corridor passes require unchanged adjacency,
matched-corridor overlap at least 0.90, bottleneck motion no greater than
$0.15\sigma_{\min}$, relative width/density change no greater than 0.10, and no
unresolved split/merge ambiguity. These are versioned conservative defaults, not physical
constants; overrides are explicit policy records.

`stage11_feature_correspondence_v1` uses the normalized cost defined in the architecture
manual with weights $(w_d,w_o,w_p)=(1,2,1)$, maximum assignment cost 3.0, ambiguity margin
0.10, deterministic lexicographic tie breaking, and explicit unmatched/split/merge
outcomes. Point-to-ridge matching is prohibited unless the candidate-type policy explicitly
allows a lineage transition. Any future change requires a new preset identifier and
regression fixtures.

# Persistent certificates

## `DensityFieldResolutionCertificate`

Required fields include:

```text
grid shapes
realized Cartesian intervals
fixed kernel covariance and signature
Delta/sigma or reciprocal-resolution metrics
CIC covariance
Gaussian-stencil covariance
effective artificial broadening
normalization residuals
backend and storage summary
scientific resource policy signature
budget-limited status
resolved or unresolved reasons
```

## `BasinGridConvergenceCertificate`

Required fields include:

```text
attractor count by level
feature correspondence
anchor displacement
basin overlap
integrated basin probability changes
split and merge records
unmatched candidates
correspondence ambiguity
accepted or unresolved reasons
```

## `CorridorGridConvergenceCertificate`

Required fields include:

```text
density-boundary adjacency by level
corridor location and width
candidate bottleneck-density changes
split and merge records
unmatched candidates
correspondence ambiguity
accepted or unresolved reasons
```

The certificates are orthogonal. A valid result may be:

```text
field numerics: converged
basins: converged
transition corridors: unresolved
```

No combined topology Boolean may erase that distinction.

# Budget behavior

The common planner may return a budget-limited ladder. Plotting may render the
finest feasible level with a visual warning.

Scientific code must instead return:

```text
unresolved_due_to_resolution_budget
```

when the requested convergence criterion was not reached. The finest affordable
field is retained as diagnostic evidence but is not promoted as authoritative.

Scientific and rendering budgets remain non-substitutable. Browser, mesh, trace,
and HTML limits cannot change a scientific grid shape or kernel.

# Cross-fitting contract

The complete-system SAMP0 partition contains either explicit discovery, model-selection, basin-validation, corridor-validation,
thermodynamic-validation, and optional-refit blocks, or a signed nested-selection policy confined to the discovery partition.

The sequence is:

```text
discovery/model-selection blocks
    -> choose bandwidth hypothesis
    -> execute fixed-kernel grid ladder
    -> select one converged numerical hypothesis
    -> freeze candidate basins and density boundaries

held-out basin-validation blocks
    -> assign with the frozen hypothesis
    -> certify basin recurrence and sampling

held-out corridor-validation blocks
    -> count independent passages
    -> certify corridor support
```

Held-out blocks cannot modify kernel covariance, grid level, candidate count, or
feature correspondence. An all-data final refit receives a new signature and
must not inherit parameter-certification evidence.

Grid convergence does not replace SAMP1/SAMP2. The former addresses numerical
discretization; the latter addresses trajectory support and event recurrence.

# Staged implementation

## GR0 - common geometry and diagnostics - implemented

Implemented in `0.20.23a0`. Grid geometry, realized intervals, periodic spread, reciprocal resolution, and artificial broadening are analysis-owned with exact compatibility parity.

## GR1 - common planner and ladder - implemented

Implemented in `0.20.24a0`. Target-shape and finest-feasible search, deterministic exact nested-grid planning, backend-independent field-reuse keys, physical-resolution-first/backend-second selection, and explicit budget-limited status are analysis-owned. See `common_grid_planning_spec.md`.

## GR2 - plotting adaptation - implemented

Implemented in `0.20.25a0`. Atomic and framework plotting consume signed GR0
geometry and optional GR1 replay plans while preserving existing visual policy,
selected grids, sparse routing, warnings, fields, meshes, scenes, and public
serialization. See `plotting_grid_adaptation_spec.md`.

## GR3 - Stage 11 scientific refinement - implemented

Implemented in `0.20.26a0`. Pilot-only hard-coded grid pairs are replaced by
`ScientificGridRefinementPolicy`; the kernel remains fixed and field, basin, and
corridor certificates remain separate. The exact runtime and stopping contract
is defined in `fixed_kernel_grid_refinement_spec.md`.

## GR4 - cross-fitted numerical-hypothesis selection and freeze

Run grid/bandwidth selection only in discovery/model-selection evidence. Freeze
the numerical hypothesis before held-out basin and corridor validation.

## GR5 - D0b-D0d ownership closeout

Move remaining numerical field contracts and producers into analysis ownership,
make plotting consume analysis-owned producers, and remove compatibility
ownership only after dense, sparse, scientific, visual, and package-wide
regressions pass.

# Failure behavior

Fail closed for:

- nonpositive or nonfinite interval/refinement controls;
- an invalid cell or singular metric;
- a kernel change inside one grid ladder;
- incompatible logical grids presented as one refinement series;
- a rendering budget passed as a scientific budget;
- held-out data used to tune the numerical hypothesis;
- silent acceptance of a budget-limited unconverged ladder;
- field-signature reuse when source, kernel, grid, or weight signatures differ.

Unresolved basin or corridor convergence is a scientific result, not an
exception, provided the underlying field is finite and valid.

# Acceptance tests

The combined regression boundary covers:

```text
tests/test_atomic_density.py
tests/test_density_contracts.py
tests/test_density_diagnostics.py
tests/test_density_broadening.py
tests/test_stage11e1_periodic_species_density.py
tests/test_stage11e2_density_attractors.py
tests/test_stage11e8a_refinement_lineage_pilot.py
```

Additional GR tests must cover:

- exact old/new common-layer numerical and serialization parity;
- orthogonal and strongly triclinic cells;
- interval-derived and explicit grids;
- dense and local-sparse parity;
- unresolved periodic means;
- reciprocal-resolution thresholds;
- CIC/stencil covariance;
- deterministic budgeted shape selection;
- fixed-kernel basin convergence with unresolved corridor topology;
- split, merge, unmatched, and ambiguous feature correspondence;
- budget-limited unresolved ladders;
- discovery/selection versus held-out isolation;
- unchanged atomic/framework plotting and browser/mesh admission.

# Explicit non-goals

This stage does not:

- make plotting meshes a scientific topology oracle;
- use visual bandwidth/grid coupling for scientific convergence;
- claim corridor convergence from basin convergence;
- treat grid convergence as sampling confidence;
- authorize a saddle, barrier, path, or rate;
- remove compatibility imports before GR5 acceptance;
- refactor the entire density, sparse, mesh, browser, and public API stack in one
  release.
