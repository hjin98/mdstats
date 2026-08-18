---
title: "Graph Visualization Specification Index"
subtitle: "Normative documentation map for implemented G1-G5"
author: "mdstats"
geometry: margin=0.82in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \usepackage{array}
    \usepackage{fvextra}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
    \RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\small}
---

# Purpose and status

This index defines the modular documentation boundary for the `mdstats`
graph-visualization subsystem.

Current status:

```text
G1-G3    implemented and validated in mdstats 0.10.0
G4-G5    implemented and validated in mdstats 0.11.0
G6       framework-topology adapter implemented in mdstats 0.13.0
Style    compact dots and edge-only node display implemented in mdstats 0.13.1
Plot-D1/D2 registered framework and trajectories implemented in mdstats 0.19.30a0
Plot-D3 atomic density implemented in mdstats 0.19.31a0
LD0-R1 through LD8-S4 and LD9-V0 through LD9-V4 implemented through mdstats 0.19.62a0
LD16 Stage 1 regression locks implemented in mdstats 0.19.74a0
LD17 Stage 2 explicit mesh-face contracts implemented in mdstats 0.19.75a0
G7-G8    architectural placeholders only
```

The former monolithic G1-G3 document
`graph_visualization_core_atomic_adapter_specification_v1.*` remains historical but is
not a normative API owner.

# AI context summary

When using these documents as implementation context, preserve the following
invariants:

1. The scientific graph remains authoritative.
2. `DecoratedGraphView` is immutable renderer input, not a scientific result.
3. Stable scientific keys are distinct from dense source positions and display keys.
4. Filtering, periodic materialization, styling, layout, and rendering never alter
   scientific graph identity.
5. Omitted nodes and edges are explicit; silent sampling is forbidden.
6. Periodic replicas and ghosts are display objects only.
7. `PeriodicGraphView` is shared by 2-D and 3-D renderers.
8. Renderers do not infer bonds, framework topology, rings, sites, or cages.
9. Atomic canonical image shifts remain distinct from frame-local display shifts.
10. Plotly remains optional and lazily imported.
11. Node-display modes alter artists only; hidden nodes remain in scientific and display mappings.
11. Framework and future ring adapters consume their scientific modules rather than
    reimplementing them.
12. Projected framework shifts remain distinct from frame-local display shifts.
13. One concept has exactly one normative specification owner.

The full separation is

$$
\text{scientific result}
\rightarrow
\text{DecoratedGraphView}
\rightarrow
\text{source selection}
\rightarrow
\text{PeriodicGraphView}
\rightarrow
\text{renderer output}.
$$

# Specification map

| Normative document | Status | Source ownership | Primary public API |
|---|---|---|---|
| [graph-view core](graph_view_spec.md) ([PDF](graph_view_spec.pdf)) | implemented | `graph_view.py`, `graph_errors.py` | graph data, focus, filters, complexity |
| [graph style](graph_styles_spec.md) ([PDF](graph_styles_spec.pdf)) | implemented | `graph_styles.py` | palettes, styles, rules, labels |
| [2-D renderer](graph_2d_spec.md) ([PDF](graph_2d_spec.pdf)) | implemented; G4 integration complete | `graph_2d.py` | physical/schematic 2-D layout and Matplotlib output |
| [atomic-connectivity adapter](atomic_connectivity_graph_spec.md) ([PDF](atomic_connectivity_graph_spec.pdf)) | implemented with 2-D and 3-D wrappers | `atomic_connectivity_graph.py` | atomic state/transition graph views and wrappers |
| [framework-topology adapter](framework_topology_graph_spec.md) ([PDF](framework_topology_graph_spec.pdf)) | implemented G6 | `framework_topology_graph.py` | projected framework and retained atomic-path views |
| [framework-dynamics overlays](framework_dynamics_spec.md) ([PDF](framework_dynamics_spec.pdf)) | implemented Plot-D1/D2 | `framework_dynamics.py` | registered mean framework and selected atomic trajectories |
| [periodic atomic density](atomic_density_spec.md) ([PDF](atomic_density_spec.pdf)) | implemented Plot-D3 | `atomic_density.py`, `framework_dynamics.py` | normalized occupancy fields and browser-stable probability-mass meshes |
| [LD2-A sparse density clouds](density_sparse_render_ld2_a_spec.md) ([PDF](density_sparse_render_ld2_a_spec.pdf)) | implemented | `density_node_cloud.py`, `framework_dynamics.py` | backend-neutral HDR details and deterministic logical-node cloud rendering |
| [LD2-B sparse density meshes](density_sparse_mesh_ld2_b_spec.md) ([PDF](density_sparse_mesh_ld2_b_spec.pdf)) | implemented | `density_sparse_mesh.py`, `framework_dynamics.py` | periodic candidate-cell meshing, clipping, seam validation, and winding fallback |
| [LD3 sparse framework density](density_framework_sparse_ld3_spec.md) ([PDF](density_framework_sparse_ld3_spec.pdf)) | implemented | `framework_density.py`, `framework_dynamics.py` | sparse framework-vertex occupancy and framework-edge arc-length channels |
| [LD4 automatic backend selection](density_backend_selection_ld4_spec.md) ([PDF](density_backend_selection_ld4_spec.pdf)) | implemented | `density_backend_selection.py`, `framework_dynamics.py` | exact transactional dense-versus-local-sparse selection |
| [LD11 default automatic density policy](density_default_auto_policy_ld11_spec.md) ([PDF](density_default_auto_policy_ld11_spec.pdf)) | implemented | `density_contracts.py`, `atomic_density.py`, `framework_density.py`, `framework_dynamics.py` | canonical periodized operator and physical-resolution-first automatic backend defaults |
| [LD5 sparse optimization and caching](density_sparse_optimization_ld5_spec.md) ([PDF](density_sparse_optimization_ld5_spec.pdf)) | implemented | `density_sparse_optimization.py`, density preparation/planning modules | optimized/reference sparse evaluation and bounded canonical-support caching |
| [density mesh simplification](density_mesh_simplify_spec.md) ([PDF](density_mesh_simplify_spec.pdf)) | implemented | `density_mesh_simplify.py` | periodic QEM reduction with seam, topology, and scalar-field fidelity checks |
| [density scene fitting](density_scene_fit_spec.md) ([PDF](density_scene_fit_spec.pdf)) | implemented | `density_scene_fit.py` | closed-loop simplification, recontouring, and exact profile compliance |
| [density mesh contracts](density_mesh_contracts_spec.md) ([PDF](density_mesh_contracts_spec.pdf)) | implemented | `density_mesh_contracts.py` | raw extraction, visual target, and standalone final face semantics |
| [browser mesh budget](density_render_budget_spec.md) ([PDF](density_render_budget_spec.pdf)) | implemented | `density_render_budget.py` | exact post-replication accounting and hard pre-write validation |
| [density scene allocation](density_scene_budget_spec.md) ([PDF](density_scene_budget_spec.pdf)) | implemented | `density_scene_budget.py` | deterministic initial canonical shell targets |
| [density mesh execution](density_mesh_execution_spec.md) ([PDF](density_mesh_execution_spec.pdf)) | implemented | `density_mesh_execution.py` | bounded isolated-worker scheduling and timeout policy |
| [browser acceptance](density_browser_acceptance_spec.md) ([PDF](density_browser_acceptance_spec.pdf)) | implemented | `density_browser_acceptance.py` | interaction metrics and physical-WebGL production gate |
| [periodic graph display](periodic_graph_spec.md) ([PDF](periodic_graph_spec.pdf)) | implemented G4 | `periodic_graph.py` | periodic display keys, materialization options and result |
| [interactive 3-D renderer](graph_3d_spec.md) ([PDF](graph_3d_spec.pdf)) | implemented G5 | `graph_3d.py` | Plotly options, result, hover, cells and HTML export |

The Graph Visualization Architecture Manual remains the high-level owner of goals,
stages, dependency policy, and future scientific adapters. It does not redefine
public dataclass fields.


# Dependency direction

```text
scientific graph result
        |
        v
scientific adapter
        |
        v
DecoratedGraphView  <---------- GraphStyle
NodeDisplayMode
        |
        v
GraphFocus and GraphFilter
        |
        v
periodic display preparation
        |
        v
PeriodicGraphView
        |
        +---------------------------+
        |                           |
        v                           v
2-D projection/layout          3-D physical rendering
        |                           |
        v                           v
Matplotlib GraphRenderResult   Plotly InteractiveGraphRenderResult
```

Dependencies flow downward. The common graph-view module imports no scientific
adapter or renderer. G4 may use the private source-selection implementation owned by
the core, but it does not redefine focus or filtering. G5 consumes G4 and never
performs independent periodic replication.

# Public API by module

## Common graph-view core

```python
DecoratedGraphView
GraphFocus
AttributeSelection
GraphFilter
GraphComplexityPolicy
GraphComplexityReport
```

The shared public exception hierarchy also originates in this layer.

## Styling

```python
ChemicalColorPalette
NodeStyle
NodeStylePatch
EdgeStyle
EdgeStylePatch
NodeStyleRule
EdgeStyleRule
GraphLabelOptions
GraphStyle
```

## Two-dimensional renderer

```python
GraphLayoutOptions
Graph2DRenderOptions
GraphRenderResult
plot_decorated_graph_2d
```

## Atomic-connectivity adapter

Implemented:

```python
graph_view_from_atomic_connectivity
graph_view_from_connectivity_transition
plot_atomic_connectivity_2d
plot_connectivity_transition_2d
```

Implemented in G5:

```python
plot_atomic_connectivity_3d
plot_connectivity_transition_3d
```

## Framework-topology adapter

```python
FrameworkGraphDisplayMode
FrameworkPathSegmentKey
graph_view_from_framework_topology
plot_framework_topology_2d
plot_framework_topology_3d
```

The projected view preserves authoritative `FrameworkEdgeKey` identity. The
atomic-path diagnostic view expands only the paths stored by `FrameworkTopology`.

## Periodic graph display

```python
PeriodicDisplayMode
PeriodicNodeRole
PeriodicEdgeRole
PeriodicNodeKey
PeriodicEdgeKey
CanonicalCellDisplay
LocalUnwrappedDisplay
ExpandedCellDisplay
PeriodicDisplayOptions
PeriodicGraphView
prepare_periodic_graph_view
```

## Interactive three-dimensional renderer

```python
Graph3DRenderOptions
InteractiveGraphRenderResult
plot_decorated_graph_3d
```

# Responsibility boundaries

## Scientific modules

Scientific modules own graph identity and physical meaning. Atomic connectivity owns
atomic graph states and transitions. Future framework and ring modules own projection,
linker contraction, primitive rings, ring geometry, sites, and cages.

## Visualization core

The core owns immutable graph-view validation, stable keys, source selection,
omission accounting, complexity limits, and common exceptions.

## Periodic preparation

G4 owns display-node replication, image assignment, winding ghosts, expanded cell
ranges, and source-to-display mappings. It performs no scientific connectivity test.

## Styling

The style module owns declarative visual encodings. Style never changes source or
display graph content.

## Renderers

Renderers own layout coordinates or physical scene assembly, artists or traces,
labels, legends, camera, and export behavior. They do not create scientific edges.

## Scientific adapters

Adapters translate scientific results into `DecoratedGraphView` and attach
scientific metadata. They may reconstruct frame-consistent quotient translations but
must not render or replicate periodic images.

# Cross-module identity rules

## Source scientific identity

Stable source node and edge keys identify scientific graph objects.

## Display identity

G4 display identities are

$$
(k_i,\mathbf q_i)
$$

for nodes and

$$
(k_e,\mathbf q_s,\mathbf q_t)
$$

for edges.

Display keys may multiply one source key across replicas. They never replace source
identity.

## Renderer identity

Matplotlib artists and Plotly traces are backend objects. Their insertion order is not
scientific identity. Render results must preserve explicit mappings back to display
and source keys.

# Filtering and periodic order

The shared order is normative:

```text
1. source focus
2. source filters
3. source omission record
4. periodic display count estimate
5. complexity enforcement
6. periodic materialization
7. style resolution
8. renderer construction
```

A renderer must not replicate first and then apply source-key filters, because that
would make filter semantics image-dependent.

# Current implementation status

## Implemented G1-G3

`mdstats` 0.10.0 provides:

- immutable decorated graph views;
- deterministic focus and filters;
- style rules and chemical palettes;
- Matplotlib 2-D physical and schematic layouts;
- atomic connectivity state and transition adapters;
- minimal renderer-local periodic unwrapping and ghost endpoints;
- Na-LTA integration fixtures and rendered diagnostics.

## Implemented G4

G4 implements generalized periodic display preparation into `periodic_graph.py` with:

- canonical-cell materialization;
- local unwrapping with residual winding ghosts;
- expanded rectangular cell ranges;
- source-to-display mappings;
- shared periodic provenance for both renderers.

## Implemented G5

G5 provides an optional Plotly backend with:

- interactive physical 3-D rendering;
- hover inspection;
- perspective and orthographic cameras;
- unit-cell wireframes;
- HTML export;
- atomic state and transition wrappers.

# Na-LTA system-integration contract

The relaxed Na-LTA fixture remains the primary visualization integration case.
Authoritative framework counts are:

```text
144 framework atoms
192 T-O edges
48 T atoms with degree 4
96 framework O atoms with degree 2
```

G4-G5 acceptance views include:

1. canonical-cell framework view;
2. local unwrapped Si-centered neighborhood;
3. expanded `2 x 2 x 1` framework view;
4. framework plus illustrative Na-O contacts;
5. perspective and orthographic 3-D variants.

Replicas and ghosts may increase display counts. Every display object must map exactly
to one authoritative source object.

# Shared input constraints

All arrays must have deterministic ordering, finite numeric values, and shapes
consistent with associated node or edge counts. Stable keys must be hashable and
unique within their layer. Metadata columns must be immutable scalar sequences or
one-dimensional arrays of the correct length.

Periodic preparation requires finite 3-D positions, a finite nonsingular cell, PBC
flags, and frame-consistent quotient edge translations. Nonperiodic axes may not
carry image translation.

No renderer may silently drop objects because of complexity. A rejecting policy must
raise; `warn_and_render` must record the exceeded limits.

# Optional dependency policy

The common graph view, styles, 2-D renderer, adapters, and periodic preparation must
not require Plotly.

Only `graph_3d.py` may import Plotly, and it must do so lazily. Packaging should expose
an optional extra such as

```text
mdstats[interactive]
```

for the 3-D backend.

# Future compatibility

The following planned adapters fit downstream of the same contracts:

```text
framework_topology_graph.py
    decorated projected framework vertices and linker-path edges

ring_graph.py
    ring incidence, ring adjacency, ring-center and normal metadata

site_and_cage_graph.py
    site, cage, and transport graphs with real-space centers
```

Future adapters must not add domain-specific fields to generic renderer options.

# Normative language

The words **must**, **must not**, **should**, **should not**, and **may** have their
usual specification meanings.

For implemented G1-G5 behavior, source and tests currently take precedence over a
document discrepancy, and the discrepancy is a defect. Specifications must be updated
deliberately whenever implementation review exposes a necessary change.

# Supersession and migration

The modular specification set supersedes the monolithic G1-G3 document.

G4 additionally supersedes renderer-local ownership of generalized periodic graph
materialization. The 2-D renderer may preserve legacy 0.10.0 options as compatibility
syntax, but periodic algorithms and source-to-display semantics belong to the G4
specification.

G5 does not supersede the 2-D renderer. Both backends share graph, style, and periodic
contracts while optimizing different use cases.

# Acceptance checklist

The G4-G5 implementation is accepted when:

- every public field and function has one normative owner;
- G4 options cannot express invalid cross-mode combinations;
- source and display identities are mathematically explicit;
- winding and expanded-cell algorithms are deterministic;
- G5 imports Plotly lazily;
- unit-cell geometry supports triclinic cells;
- hover and trace mappings preserve source keys;
- complexity and unsupported features have explicit policies;
- atomic 3-D wrappers reuse existing adapters;
- Na-LTA interactive acceptance cases are fixed;
- Markdown and PDF versions have heading and equation parity.

- [LD6 multilevel density research gate](density_multilevel_research_ld6_spec.md)

# LD8-P0 and LD9-V0 density optimization specifications

- [LD8-P0 production-cutoff evidence](density_evidence_benchmark_ld8_p0_spec.md)
- [LD9-V0 hard browser render budget](density_render_budget_spec.md)
- [LD9-V0 mesh fidelity and topology validation](density_mesh_validation_ld9_v0_spec.md)


- [LD8-S0 periodic kernel block routing](density_block_routing_ld8_s0_spec.md)
- [LD8-S1 exact periodic support atlas](density_support_atlas_ld8_s1_spec.md)
- [LD8-S0 packed scientific field contract](density_packed_field_ld8_s0_spec.md)
- [LD8-S2 canonical target-owned direct realization](density_block_direct_ld8_s2_spec.md)

- [LD8-S3 hybrid tiled direct/FFT realization](density_tiled_fft_ld8_s3_spec.md)
- [LD12 hybrid-aware scene admission](density_hybrid_scene_admission_ld12_spec.md)
- [LD8-S4 production dispatch and downstream reuse](density_downstream_reuse_ld8_s4_spec.md)
- [LD9-V1 bounded tiled contour extraction](density_tiled_contour_ld9_v1_spec.md)



# Interactive density mesh module specifications

- [Density mesh face contracts](density_mesh_contracts_spec.md)
- [Exact browser mesh budget](density_render_budget_spec.md)
- [Scene-wide shell allocation](density_scene_budget_spec.md)
- [Closed-loop density scene fitting](density_scene_fit_spec.md)
- [Periodic density-mesh simplification](density_mesh_simplify_spec.md)
- [Bounded mesh-worker execution](density_mesh_execution_spec.md)
- [Browser functional and production acceptance](density_browser_acceptance_spec.md)
- [Framework dynamics and partitioned topology rendering](framework_dynamics_spec.md)

The former Stage-1, Stage-2, combined Stages-2--9, and LD9-V0/V2/V3/V4
chronological documents have been absorbed into these module-owned specifications.
