# mdstats 0.20.150a0

## GFX3D-5 - universal rendering and interaction semantics

This release closes the foundational GFX3D-1 through GFX3D-5 architecture.

### Renderer-neutral layer output

- Removed the temporary built-in `source_scene` renderer reference from prepared framework, connectivity, trajectory, and density layer products.
- Built-in layer adapters now emit renderer-neutral `PointSet3D`, `SegmentSet3D`, `PolylineSet3D`, `TriangleMesh3D`, and `CellWireframe3D` primitives directly from already-prepared scientific products.
- Replaced the GFX3D legacy-composite Plotly composition path with a generic primitive-only Plotly backend.
- The common renderer contains no built-in framework/connectivity/trajectory/density dispatch. A mock fifth registered layer renders without modifying the common result schema.

### Universal interaction and view semantics

- Named layers are independent legend/visibility groups; Plotly group-click toggles one whole layer.
- Added render-only integer layer `priority`; declaration order remains the deterministic tie-break.
- Added scene-level `visible_layers` initial-state override.
- Added reproducible camera/view semantics: orthographic/perspective projection, explicit camera eye, and `[100]`, `[010]`, `[001]`, `[110]`, `[101]`, `[011]`, `[111]`, and `isometric` presets.
- Added scene-wide periodic display replication through canonical, `NxMxK`, explicit-shift, and count/origin forms.
- Periodic replication is a view transformation over prepared primitives and does not alter density normalization, trajectory weights, connectivity occupancy, or scientific identities.
- Added universal background, axis, width, height, and cell visibility controls.

### Browser payload authority

- Added renderer-neutral browser payload accounting for trace count, point count, segment count, triangle faces, and estimated geometry bytes.
- Added explicit compact/balanced/quality browser budgets.
- Budget failures raise a clear error; requested layers are never silently dropped.
- Per-layer payload contribution and total payload/budget records are render evidence only.

### CLI/config additions

Added:

- `--camera`
- `--periodic-images`
- `--cell-mode`
- repeatable `--visible-layer`
- `--show-axes`
- `--background`
- `--width`
- `--height`
- TOML `[[layer]].priority`
- matching `[scene]` view records.

### Scientific invariance

Using the supplied 300 K Na-LTA MLFF trajectory at stride 500 (21 frames x 168 atoms), GFX3D-5 reproduces the `0.20.149a0` scientific products exactly:

- mean-framework coordinate SHA-256: `a646f0712ef8aa0c49f06826367a83848a8273f7a0803c7e5ff7ce938764025e`
- Na trajectory coordinate SHA-256: `bd1184330923381803db1e0f09cab8e93605fb4b6e954cd95074367e019635be`
- Na density SHA-256: `7dfe8c055122a0a5ee1ab47fe50c1f827158aa65447057794936e5544747a9f8`
- density integral: `23.999999999999996`
- density-planning approval ID: `0d0c876f4aa4f87ec6795bd04944017838bfe0eab11a8c6d70e66c15906132cc`

A 2x1x1 `[111]` renderer-neutral qualification produces 20 Plotly traces and 149,896 displayed density faces with about 5.46 MB of estimated geometry payload. Only the explicitly requested Na-density layer starts visible. Built-in prepared layer products contain zero renderer-only `source_scene` references.

### Tests

Focused GFX3D/framework/renderer qualification:

- **83 passed**
- **0 failed**
- **0 skipped**

The warning stream consists only of the existing legacy equal-aspect/orientation diagnostics exercised by compatibility tests.

### Next visualization extension

The universal GFX3D foundation is now complete. The next scientific visualization gate is `GFX3D-RING1`, which should expose the existing ring scientific authority through the stable layer/primitive architecture.
