# mdstats 0.20.147a0 patch notes

## GFX3D-2 - independent graphical layers

This revision completes the second universal 3-D graphics gate without changing the scientific definitions of the existing framework, connectivity, trajectory, or density products.

### Added

- registered `FrameworkTopologyLayer`, `AtomicConnectivityLayer`, `AtomicTrajectoryLayer`, and `AtomicDensityLayer` adapters under `mdstats.graphics3d`;
- `prepare_graphics3d_scene()` for deterministic preparation of enabled independent layer instances from one shared `GraphicsSceneContext`;
- one shared prepared `FrameworkDynamicsScene` dependency for the GFX3D-2 migration path, resolved once through the scene cache;
- scientific filtering for prepared trajectory selections and averaged atomic-connectivity species/atom/pair selections;
- fail-closed prepared density-field selection using exact field/provenance/atom evidence;
- `render_graphics3d_plotly()` as the common layer-keyed Plotly composition path;
- generic layer trace ownership through `Graphics3DRenderResult` / `GraphicsLayerRenderResult`;
- support for multiple instances of the same graphical layer type with independent render identity.

### Compatibility

- `FrameworkDynamicsScene` remains the current qualified scientific preparation product;
- the GFX3D-2 adapters do not recompute framework topology, connectivity, trajectory paths, or scalar density fields;
- the common Plotly composer reuses the existing qualified legacy rendering routines as a backend compatibility engine;
- the existing `plot_framework_dynamics_3d()` path remains unchanged and tested.

### Focused qualification

The focused suite covers:

- all 15 non-empty combinations of framework/connectivity/trajectory/density;
- duplicate trajectory and density instances;
- pair-filtered atomic connectivity;
- fail-closed absent density selection;
- GFX3D-1 contracts and legacy scene/result adapters;
- existing framework-dynamics and canonical 3-D graph rendering.

Result: **62 passed, 0 failed, 0 skipped**.

The observed warnings are the existing equal-aspect/orientation diagnostics from the legacy Plotly renderer.

## Next gate

GFX3D-3 - universal CLI and declarative configuration.
