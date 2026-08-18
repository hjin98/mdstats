---
title: "Stage 11E-GR2 Plotting Grid Adaptation"
subtitle: "Atomic/framework compatibility over common grid geometry and planning"
author: "mdstats"
date: "2026-07-27"
version: "0.20.25a0"
status: "implemented in revision 55; retained under architecture revision 56"
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

Stage 11E-GR2 adapts the existing atomic- and framework-density plotting paths to
the common Stage 11E-GR0 grid geometry and Stage 11E-GR1 logical-grid planning
records. It is a compatibility refactor. It does not introduce a new estimator,
change a visual default, alter dense/local-sparse routing, or promote a plotted
field to a scientific convergence certificate.

The current visual policy remains authoritative for plotting:

$$
\sigma = c\,\max_i \Delta_i,
$$

unless the user supplies an explicit Gaussian bandwidth. When spread-aware
visual refinement is enabled, plotting may continue to refine the grid and
visual Gaussian width together. This coupled refinement is useful for display,
but it is not a scientific convergence certificate and is not the fixed-kernel
grid refinement required by Stage 11E-GR3.

# Ownership boundary

GR2 introduces a plotting-owned `DensityVisualGridAdaptation` record. The record
contains:

- one analysis-owned `DensityGridGeometry`;
- an optional analysis-owned `DensityLogicalGridPlan` replay for automatic grids;
- the unchanged plotting visual-bandwidth policy and adaptive outcome;
- graph-facing diagnostic metadata and warning codes; and
- a canonical SHA-256 signature.

`mdstats.analysis.density` remains independently importable without Plotly,
mesh, browser, graph, or HTML policy. GR2 does not move field production,
periodized kernels, support masks, HDR integration, or sparse execution; those
remain later GR5 ownership work.

# Atomic and framework adapters

Both `prepare_atomic_density_fields` and `prepare_framework_density_fields` must
construct one adaptation record immediately after resolving their visual
numerics. The adapters must then consume the common geometry for:

- selected grid shape;
- realized Cartesian grid intervals;
- logical node count; and
- the signed logical-grid identity.

The plotting resolver remains responsible for:

- explicit versus interval-derived grid choice;
- visual Gaussian-to-grid coupling;
- spread-aware trigger conditions;
- effective-CIC/stencil visual broadening;
- warning emission; and
- budget-limited visual fallback.

The framework vertex and edge fields share the same selected visual grid and
visual bandwidth. Edge quadrature retains its independent field-specific
broadening diagnostic.

# Automatic-grid replay

For interval-derived grids, GR2 constructs a GR1 plan that replays the already
resolved visual grid. The replay target interval is chosen from the open
interval of Cartesian spacings that maps exactly to the selected integer grid
shape. This prevents floating-point boundary ambiguity and does not reinterpret
the visual target as a scientific target.

The plan metadata must identify its role as `selected_visual_grid_replay`.
The signed `grid_definition` value is `target_lattice_interval` for this path.
Explicit `grid_shape` requests use `grid_definition=explicit_shape` and do not
require a GR1 search plan; their common GR0 geometry is still recorded and
signed.

# Metadata compatibility

Existing field metadata keys and values are preserved. The adaptation record
provides helper views that reproduce the established dictionaries for:

- grid definition and realized intervals;
- visual Gaussian bandwidth and coupling ratio;
- adaptive trigger, target, achievement, and budget-limited state;
- periodic spread diagnostics;
- reciprocal-resolution diagnostics; and
- effective artificial-broadening diagnostics.

No browser, mesh, trace, scene, or HTML budget is accepted by the adaptation
API. Existing browser/mesh/scene admission remains downstream and unchanged.

# Error translation

Analysis numerical-input failures are translated to `GraphAdapterError` or
`GraphStyleError` according to the existing plotting contract. Common resource
failures are translated to `GraphComplexityError`. Serialization or signature
mismatch is a graph-adapter failure.

GR2 fails closed when:

- the resolved shape differs from common geometry;
- realized intervals do not match the common cell metric;
- an automatic replay plan selects a different grid;
- the visual Gaussian or ratios are invalid;
- adaptive target state is internally inconsistent;
- a replayed plan is bound to another cell or grid; or
- serialized content is tampered with.

# Regression requirements

The following must remain unchanged:

- atomic and framework density scalar values;
- default and explicit selected grids;
- visual bandwidths and warnings;
- dense/local-sparse/auto routing;
- backend-selection metadata;
- public option dataclass serialization and equality;
- mesh extraction and simplification;
- browser and scene admission; and
- graph-facing exception classes.

Focused tests cover signed replay, tamper rejection, explicit-grid adaptation,
automatic-grid GR1 replay, adaptive budget-limited state, strongly triclinic
geometry, atomic/framework integration, metadata parity, and absence of plotting
imports from `mdstats.analysis.density`.

# Implementation status

Implemented in `0.20.25a0`. Architecture revision 56 retains GR2 as complete
and records Stage 11E-GR3 fixed-kernel scientific grid refinement as implemented
in `0.20.26a0`. Stage 11E-GR4 is the next implementation stage.
