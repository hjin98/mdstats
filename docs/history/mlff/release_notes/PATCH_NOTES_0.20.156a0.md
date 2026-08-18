# mdstats 0.20.156a0 patch notes

## GFX3D-HARDEN1 - existing-layer robustness

- Hardens the universal 3-D plotting stack before ring/cage/site extensions without changing the scientific definitions of framework, connectivity, trajectory, or density layers.
- Replaces the previous write-only LTA topology sidecar with an authenticated `mdstats.graphics3d.topology-cache.v2` envelope. Exact trajectory geometry/frame identity, framework-connectivity definition, and framework mapping are verified before reuse; legacy or mismatched caches are rejected and recomputed rather than silently trusted.
- Removes the residual composite `FrameworkDynamicsScene` object from `GraphicsScientificProduct`. Raw GFX3D products now carry only their renderer-neutral scientific value plus display-cell/frame/provenance metadata; density products use an explicit `GraphicsDensityProduct` bundle.
- Moves unit-cell wireframe ownership to the scene/view renderer so framework-, connectivity-, trajectory-, and density-only scenes obey the same `cell_mode` semantics.
- Restores universal trajectory hover metadata, including atom/species/frame/frame-id/time information, on renderer-neutral trajectory polylines.
- Makes camera and periodic-image parsing fail closed: non-finite vectors, zero eye/up vectors, fractional counts/origins, malformed explicit shifts, and unknown view keys are rejected instead of truncated or accepted ambiguously.
- Adds browser-payload preflight before periodic arrays are materialized, then verifies the realized payload against the prediction. Oversized replicated scenes fail before large display-only copies consume memory.
- Adds a uniform-catalog fast path and a GFX3D-only dominant-category fast path. The latter preserves the dominant framework/connectivity products while avoiding materialization of non-dominant category render objects that current universal layers do not consume; legacy `prepare_framework_dynamics_scene()` retains full-category behavior by default.
- Hardens long-trajectory framework geometry: retained atomic-path MIC vectors are batched per frame, static-cell projected geometry is vectorized across the full selected frame set, and only canonical graph-view metadata is retained. On the supplied 10,001-frame Na-LTA trajectory with a fixed topology, framework preparation completed in about 11.23 s; the projected framework-registration stage itself completed in about 0.5 s. A 1,001-frame comparison dropped from about 13.17 s before the static-cell bulk path to about 1.17 s after it.
- Keeps variable-cell and periodic-multiedge cases on the established exact frame-local path; the bulk fast path is guarded by first-frame scientific-equivalence checks and dedicated regression coverage.
- Repairs the stale PAR-DENS architecture test so it checks the current package version from `pyproject.toml` rather than pinning the historical `0.20.145a0` release.
- Final focused GFX3D/framework/density qualification: 117 tests passed, including the hardening, GFX3D-1 through GFX3D-5, framework dynamics, topology visualization, PAR-DENS architecture/preprocessing, and density backend-selection surfaces.
