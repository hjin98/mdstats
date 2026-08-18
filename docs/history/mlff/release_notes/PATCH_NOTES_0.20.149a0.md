# mdstats 0.20.149a0 patch notes

## GFX3D-4 - shared dependency planning and cache authority

This release completes GFX3D-4.  The universal 3-D graphics stack now plans
scientific products at layer granularity rather than treating one prepared
`FrameworkDynamicsScene` as the scientific dependency of every layer.

### Product-level dependency authority

The four currently implemented layer families declare distinct scientific
providers:

- `framework_topology_product`
- `atomic_connectivity_product`
- `atomic_trajectory_product`
- `atomic_density_product`

A scene containing only a subset of those layers plans only that subset of
product dependencies.  Duplicate layer instances with the same scientific
request share one dependency key.

The current LTA/framework-dynamics scientific owner is intentionally allowed to
batch compatible products internally.  This preserves the qualified existing
scientific algorithms while exposing product-level authority to GFX3D.  On the
real Na-LTA all-four-layer qualification, four product dependencies were served
from one qualified framework-dynamics preparation.

### Single-flight cache semantics

`GraphicsSceneContext` now provides in-memory single-flight dependency
resolution.  Concurrent misses for the same scientific dependency execute the
resolver once; other consumers wait for and reuse the same result.  Resolution
order and cache state are execution evidence only and do not alter scientific
identity.

Dependency results are collated deterministically in the canonical dependency
plan order even when independent resolution begins concurrently.

This gate intentionally does not introduce a durable GFX3D product cache.
Durable scientific caches owned by existing subsystems remain authoritative.

### CLI and manifest behavior

The GFX3D-3 CLI now creates a lazy scientific dependency source.  Therefore
`--manifest-only` can expose the exact product-level dependency plan without
executing topology, connectivity, trajectory-preparation, or density work.

A real preparation uses the same dependency source and shared
`GraphicsSceneContext`.  Dependency-level timing/cache evidence and source
batch-preparation evidence are recorded separately from scientific identities.

### Scientific equivalence

The supplied 300 K Na-LTA MLFF trajectory was requalified at stride 500
(21 frames, 168 atoms).  Compared with 0.20.148a0, 0.20.149a0 produced exactly
identical hashes for:

- mean framework positions;
- Na trajectory positions;
- Na density field values.

The Na density integral remained `23.999999999999996`, and the density-planning
approval ID remained
`0d0c876f4aa4f87ec6795bd04944017838bfe0eab11a8c6d70e66c15906132cc`.

This is an architecture/cache-authority gate, not a numerical-kernel
optimization gate; no wall-time speedup claim is made.

### Focused qualification

Focused GFX3D/framework/renderer qualification passes **74 tests** with no
failures or skips.  This includes concurrent single-flight resolution,
duplicate dependency deduplication, product-level plans, cache-neutral
identity, all GFX3D-1/2/3 contracts, CLI behavior, and legacy rendering
compatibility.

### Compatibility boundary

`FrameworkDynamicsScene` remains a qualified scientific-owner batch and a
temporary compatibility reference for the current Plotly renderer.  Layers no
longer depend scientifically on a monolithic scene key.  GFX3D-5 will remove
this remaining renderer coupling by completing renderer-neutral layer
primitives and universal interaction semantics.
