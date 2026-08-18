# mdstats 0.20.146a0 patch notes

## GFX3D-1 - universal 3-D graphics contracts

This revision establishes the contract foundation for the universal configurable 3-D graphics subsystem without changing the scientific definitions or numerical behavior of the existing framework, connectivity, trajectory, or density plotting paths.

### New `mdstats.graphics3d` package

GFX3D-1 introduces:

- immutable `GraphicsSelection`, `GraphicsLayer3DRequest`, and `GraphicsScene3DRequest` records;
- explicit scientific, render, and execution identity domains;
- scientific-only `GraphicsDependencyKey` / dependency-request contracts and deterministic deduplication;
- `GraphicsSceneContext` with an in-memory scientific dependency cache foundation;
- deterministic `GraphicsLayerRegistry` and registration metadata;
- canonical `GraphicsSceneManifest` JSON serialization and SHA-256 identity;
- renderer-neutral point, polyline, segment, triangle-mesh, arrow, text-label, cell-wireframe, and legend-group primitives;
- generic layer-keyed `Graphics3DRenderResult`;
- compatibility adapters for current `FrameworkDynamicsScene` and `FrameworkDynamicsRenderResult`;
- the canonical GFX3D architecture manual and initial formal CLI-specification skeleton.

Layer names are required to be unique. Render-only changes do not affect scientific layer identity, scientific selection/analysis changes do, and resource/executor evidence remains separately identified. Equal scientific dependency keys deduplicate independently of consumer names.

### Compatibility

`FrameworkDynamicsScene`, `FrameworkDynamicsRenderResult`, `prepare_framework_dynamics_scene`, `plot_framework_dynamics_3d`, and the current LTA hybrid example remain scientifically unchanged. GFX3D-1 adapts their already-prepared products; it does not re-run or reinterpret their science.

### Focused qualification

The GFX3D contract tests plus existing framework-dynamics and generic 3-D renderer tests pass: **42 passed**. Existing equal-aspect/orientation runtime warnings remain unchanged.

The next gate is **GFX3D-2**, which decomposes framework topology, atomic connectivity, atomic trajectory, and atomic density into independent registered layer adapters.
