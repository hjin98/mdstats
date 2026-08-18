---
title: "Scientific Density Analysis Facade"
subtitle: "Stage 11E0a: canonical imports, compatibility production, and ownership boundary"
author: "mdstats"
date: "2026-07-25"
version: "0.19.97a0"
status: "implemented"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.82in
fontsize: 10pt
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Purpose and stage boundary

Stage 11E0a creates the canonical analysis entry point:

```python
mdstats.analysis.density
```

The stage establishes **scientific ownership** without performing the larger
a deferred density-extraction ownership move. The current numerical implementations remain in:

```text
mdstats.plotting.atomic_density
mdstats.plotting.framework_density
```

and are recorded as temporary numerical owners. The facade wraps their exact
fields in analysis-owned adapters.

The boundary is:

```text
analysis request + scientific resource policy
        -> current numerical producer
        -> exact current field object
        -> zero-copy scientific adapter
        -> scientific field bundle
```

No renderer participates in this path.

# Canonical public functions

## Atomic density

```python
prepare_atomic_density_fields(
    collection,
    *,
    frame_indices,
    frame_weights,
    display_cell,
    registration_mode,
    framework_drift,
    selections,
    options,
    registration_view=None,
    resources=None,
    planning_metadata_by_field=None,
    progress=None,
    progress_callback=None,
) -> ScientificDensityFieldBundle
```

`selections` and `options` remain the existing
`AtomicDensitySelection` and `AtomicDensityOptions` compatibility objects.
The facade forwards only scientific limits.

## Framework density

```python
prepare_framework_density_fields(
    *,
    vertex_fractional_by_frame,
    vertex_atom_indices,
    edge_segments_fractional_by_frame,
    edge_atom_indices,
    frame_weights,
    display_cell,
    registration_mode,
    options,
    consumer_registration_signature=None,
    scientific_drift_owner=None,
    resources=None,
    planning_metadata_by_field=None,
    vertex_source_keys=None,
    edge_source_keys=None,
    progress=None,
    progress_callback=None,
) -> ScientificDensityFieldBundle
```

Vertex occupancy and edge arc-length channels retain distinct units and source
provenance. The wrapper preserves the current framework container metadata in
the bundle without changing either field.

# Ownership metadata

Every bundle records:

```text
facade_stage = 11E0a
scientific_owner = mdstats.analysis.density
numerical_owner = current compatibility module
rendering_policy_consumed = false
mesh_constructed = false
browser_budget_consumed = false
```

Atomic and framework registration provenance remain on the underlying fields.
The facade does not reinterpret the spatial registration.

# Canonical compatibility imports

The following current numerical option/field classes are available lazily from
`mdstats.analysis.density`:

```text
AtomicDensityOptions
AtomicDensitySelection
PeriodicScalarField3D
FrameworkDensityOptions
FrameworkDensityFields
DensityResolutionOptions
DensityKernelOptions
DensityStorageOptions
DensityOptimizationOptions
DensitySourceProvenance
DensityStorageSummary
PeriodicWeightedSamples3D
```

Rendering option classes are intentionally absent. In particular the facade
does not export atomic/framework 3-D render options.

Root aliases use explicit scientific names:

```text
prepare_scientific_atomic_density_fields
prepare_scientific_framework_density_fields
```

This avoids collision with historical plotting-local helpers.

# Numerical equivalence

For identical inputs and scientific limits, let $F_{\mathrm{legacy}}$ be the
field produced by the current module and $F_{\mathrm{facade}}$ the unwrapped
field in the Stage-11E0a bundle. The acceptance contract is:

$$
F_{\mathrm{facade}} \equiv F_{\mathrm{legacy}},
$$

including:

- field concrete type;
- dense or sparse storage;
- scalar values;
- logical grid;
- normalization;
- total measure;
- HDR thresholds;
- source provenance; and
- metadata.

The adapter may add ownership metadata only outside the field.

# Rendering independence

Scientific preparation must succeed without:

- importing Plotly at call time;
- importing scikit-image at call time;
- extracting a mesh;
- simplifying a mesh;
- evaluating a browser mesh budget; or
- creating HTML.

The facade has no render-option or render-policy argument. A later plotting
adapter may consume the returned field protocol.

# Failure behavior

The facade fails closed for:

- an invalid collection;
- empty atomic selection sequence;
- a wrong compatibility option/selection type;
- a non-scientific resource policy;
- failures raised by the owning numerical producer;
- a resulting object that does not satisfy the scientific field protocol; or
- invalid bundle construction.

It does not catch and relabel numerical errors whose ownership remains in the
current producer.

# Acceptance requirements

- Atomic facade fields are exactly equal to the current numerical oracle.
- Framework vertex and edge fields are exactly equal to the current oracle.
- Dense field adapters are zero-copy.
- Scientific resource signatures are retained in bundles.
- Rendering/browser admission is not invoked.
- Optional rendering libraries are not required for field construction.
- Canonical analysis and root exports are present.
- Render option classes are absent from the analysis facade.
- Existing plotting APIs and numerical classes remain regression-compatible.

# Deferred density-extraction ownership move

Stage 11E0a does not move:

- field concrete classes;
- weighted-sample contracts;
- kernel contracts or implementation;
- direct/sparse realization;
- normalization and HDR logic;
- scientific planning implementation; or
- source-provenance concrete classes.

Revision 44 decomposes those moves into GR0-GR5. GR0/GR1 extract the common
grid, spread, broadening, and budgeted-planning layer; GR2 adapts plotting; GR3/GR4
add fixed-kernel scientific convergence and cross-fitting; GR5 completes the remaining
numerical ownership move. Compatibility imports and dense/sparse numerical regression
remain mandatory throughout. Stage 11E0b is reserved for the registered raw sample catalog.

# Method provenance

No new scientific estimator is introduced. Existing cloud-in-cell, periodized
Gaussian, and highest-density-region methods retain their original source
citations in the current numerical specifications. The canonical facade,
zero-copy result boundary, lazy compatibility imports, and resource ownership
split are project-specific constructions.
