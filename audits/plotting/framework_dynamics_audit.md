# Registered Framework-Dynamics Implementation Audit

Release: `mdstats 0.19.30a0`

## Implemented source boundary

- `mdstats/plotting/framework_dynamics.py`
- public exports from `mdstats.plotting` and `mdstats`
- `tests/test_framework_dynamics.py`
- `docs/specs/plotting/framework_dynamics_spec.{md,pdf}`

## Scientific separation

The implementation keeps preparation independent of Plotly. The prepared
`FrameworkDynamicsScene` contains one immutable mean `DecoratedGraphView` and an
optional immutable `TrajectoryPathSet`. The renderer only consumes those records
and appends Plotly traces to the existing generic graph result.

No connectivity, framework projection, ring discovery, site assignment, or hop
classification is repeated in the plotting layer.

## Periodic geometry

Every selected frame is first adapted by the existing authoritative framework
visualization adapter. A deterministic spanning-forest gauge lifts wrapped graph
nodes into a connected display placement. The trajectory anchor fixes the global
integer shift, while ensembles use independent canonical placement.

The transformed residual edge shifts are checked across every selected frame.
Consequently, the averaged view preserves scientific node and edge identity and
periodic winding even though tree-edge image shifts may be absorbed into node
placements.

## Registration policies

Implemented modes:

- `material`: lifted fractional geometry mapped into one display cell;
- `laboratory`: geometry mapped with each instantaneous cell before averaging;
- `framework_registered`: material geometry after removing the framework-centroid
  translation relative to the first selected frame.

The same framework drift is removed from selected atom paths. No rotation or affine
best-fit alignment is performed.

## Trajectory semantics

`TrajectoryAtomSelection` resolves the union of explicit atom indices and supplied
species. A requested path requires trajectory semantics. Continuous paths retain
unwrapped lattice motion. Folded paths wrap into the display cell and insert
explicit segment breaks when the lattice image changes.

## Renderer

`plot_framework_dynamics_3d()` delegates the framework to
`plot_decorated_graph_3d()`, then appends one line trace per selected atom and
optional grouped start/end markers. Hover records preserve atom index, element,
collection frame, source frame ID, and time when present.

## Resource boundary

Transactional limits cover selected frames, atoms, path points, trajectory traces,
and the final composite Plotly trace count. No scientific path is silently
resampled or decimated.

## Deferred scope

The release does not implement atomic density, framework vertex density, framework
edge-length density, time-window densities, site-colored paths, or hop detection.
Those features must consume the registration semantics introduced here.

## Verification

- 10 new Plot-D1/D2 tests pass;
- 25 existing framework/generic plotting tests pass in the same plotting group;
- the established 260-test topology-through-Stage-11 boundary remains green;
- Python bytecode compilation passes;
- the 8-page normative PDF passes preflight and full-page rendering inspection;
- wheel/source-distribution installation and content checks are release gates.

No external scientific algorithm was adapted. The implementation uses project-owned
periodic graph gauges, standard affine coordinate transformations, arithmetic means,
and piecewise-linear display segments.
