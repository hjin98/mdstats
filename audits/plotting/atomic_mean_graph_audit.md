# Plot-D5 atomic mean graph audit

## Scope

This audit covers the Plot-D5 extension that adds an averaged atomic
connectivity net to the existing framework-dynamics 3-D scene.

## Implemented items

- Added `AtomicMeanGraphOptions` for persistent and occupancy-threshold modes.
- Added `AtomicMeanGraph` as a prepared scientific payload on
  `FrameworkDynamicsScene`.
- Added `AtomicMeanGraph3DRenderOptions` for Plotly styling.
- Extended `prepare_framework_dynamics_scene(...)` with
  `atomic_connectivity` and `atomic_mean_graph_options`.
- Extended `plot_framework_dynamics_3d(...)` to render species-colored atomic
  nodes plus a periodic bond trace.
- Added focused tests for occupancy filtering, uniform-state input, and
  rendering trace emission.

## Scientific notes

The averaged atomic net reuses the same display cell and registration boundary
as the framework-dynamics scene. Atomic nodes are averaged in registered
coordinates. Bond occupancies are computed over the selected frames and are
retained either in `persistent` or `occupancy` mode.

## Current limitations

- Active atom scope must remain constant across the selected frames.
- The implementation is aimed at stable or weakly fluctuating bonded nets.
  Strongly reactive trajectories may require stricter thresholds or future
  per-regime handling.
