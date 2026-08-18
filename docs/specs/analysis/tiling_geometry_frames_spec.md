---
title: "Compatible-Frame Natural-Tile Geometry Specification"
subtitle: "Stage 11B: Source-Bound Gauge Replay, Dynamic Tile and Window Descriptors, and Explicit Frame Compatibility"
author: "mdstats"
date: "2026-07-19"
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

Stage 11B maps one already certified periodic natural tiling onto compatible
trajectory or ensemble frames without changing its scientific identity:

```text
certified natural tiling + exact reference geometry
        + atomistic frame collection
        + source-bound atomic connectivity
        + projected framework topology catalog
        -> replay canonical periodic vertex gauge
        -> map fixed scientific faces, windows, and tiles
        -> compute frame-dependent geometry
        -> preserve explicit unresolved frame states
```

Runtime/API target:

```text
mdstats 0.19.29a0
```

Primary module:

```text
mdstats/analysis/tiling_geometry_frames.py
```

Stage 11B is a descriptive geometry layer. It does **not** rediscover rings,
faces, tiles, or natural-tiling identity in each frame. A frame is mapped only
when its exact projected framework graph agrees with the source graph of the
certified `PeriodicCellComplex`.

# Scientific invariants

The implementation preserves the following separation.

## Persistent scientific identity

The following remain fixed across all mapped frames:

- primitive-ring keys;
- scientific face placements and orientations;
- tile attaching maps;
- topological-window identity;
- translation-labelled tile adjacency; and
- tile labels and orbit identity.

Frame geometry is evidence attached to those identities. It cannot add, remove,
or relabel scientific cells.

## Frame compatibility

Compatibility is stronger than matching atom counts. For each selected frame:

1. its atomic connectivity state is projected using the same
   `FrameworkMapping` and projection policy as the supplied `TopologyCatalog`;
2. the resulting `FrameworkTopology.graph_digest` must equal
   `PeriodicCellComplex.topology_graph_digest`;
3. the atomic periodic image gauge must be reconstructible from the declared
   unique-minimum-image connectivity convention; and
4. the reconstructed tile surfaces must remain nondegenerate, orientation
   preserving, and volume closing.

Failure at one frame does not invalidate other frames. It produces an explicit
per-frame status.

## Nonplanar dynamic faces

Reference scientific faces are exact planar polygons. Thermally distorted frame
faces need not be planar. Stage 11B retains their fixed boundary order and uses a
deterministic boundary-center fan surface for area, volume, and first-moment
integration. Planarity and projected-aperture fields are descriptive diagnostics;
they do not redefine the face.

# External methods and original construction

The translation-labelled periodic quotient convention is inherited from Chung,
Hahn, and Klee [1]. Natural-tile identity is inherited from the Stage-10/11
construction based on Blatov and coauthors [2]. Singular-value decomposition for
best-fit plane diagnostics is standard numerical linear algebra background and is
not treated as a borrowed domain algorithm.

The following mechanisms are project-specific `mdstats` constructions:

- exact replay of the composed atomic, relevant-subgraph, and projected-framework
  image gauges used by the existing connectivity/topology pipeline;
- trajectory anchor alignment to the collection's unwrapped fractional
  coordinate without changing intrinsic geometry;
- independent ensemble wrapping with no cross-frame continuity assumption;
- fixed scientific side reconstruction from source-bound ring walks and attaching
  translations;
- deterministic nonplanar boundary-center fan integration;
- explicit separation of topology mismatch, connectivity/geometry mismatch, and
  degenerate mapped geometry; and
- source-replayed persistent frame catalogs with independent geometry and
  connectivity binding digests.

No external trajectory pore-tracking, deforming-cell tessellation, dynamic
Voronoi, or maximum-clearance algorithm is claimed.

# Public API

```python
map_tiling_geometry_to_frames(
    reference_geometry: TilingGeometryCatalog,
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    topology_catalog: TopologyCatalog,
    *,
    frame_indices: Sequence[int] | None = None,
    options: FrameTilingGeometryOptions | None = None,
    resources: FrameTilingGeometryResources | None = None,
) -> FrameTilingGeometryCatalog
```

Required source equalities include

```text
reference_geometry.periodic_cell_complex_digest == complex_.digest
reference_geometry.periodic_net_embedding_digest == embedding.digest
reference_geometry.primitive_ring_catalog_digest == ring_index.catalog_digest
complex_.topology_graph_digest == ring_index.topology_graph_digest
collection.frame_semantics == topology_catalog.frame_semantics
```

The connectivity result must declare

```text
metadata["unique_minimum_image_only"] == True
```

because Stage 11B replays the physical atomic image gauge under that exact
convention. The implementation does not guess a projected-net nearest image.

# Periodic gauge replay

Let atom $i$ have wrapped fractional coordinate $\bar{\mathbf f}_i$ in one
frame. The atomic connectivity state stores canonical edge shifts
$\mathbf s_{ij}$. The physical minimum-image atomic edge has raw shift
$\mathbf m_{ij}$. The atomic canonicalization gauge $\mathbf a_i$ satisfies

$$
\mathbf s_{ij}
=
\mathbf m_{ij}+\mathbf a_j-\mathbf a_i.
$$

The framework projection then applies two additional integer gauges already
encoded by its deterministic normalization:

- $\mathbf h_i$: relevant-subgraph gauge;
- $\mathbf g_i$: final projected-framework gauge.

The frame coordinate of a canonical framework vertex is reconstructed as

$$
\mathbf q_i
=
\bar{\mathbf f}_i
+
\mathbf a_i+
\mathbf h_i+
\mathbf g_i+
\mathbf G,
$$

where $\mathbf G\in\mathbb Z^3$ is one global placement shift.

For a trajectory, $\mathbf G$ aligns one deterministic anchor vertex with the
collection's unwrapped fractional coordinate. This preserves whole-cell
continuity. For an ensemble, $\mathbf G$ independently places the anchor in the
reference cell; no temporal continuity is inferred.

A lifted vertex reference $(i,\mathbf n)$ is then mapped to

$$
\mathbf f_{i,\mathbf n}=\mathbf q_i+\mathbf n,
\qquad
\mathbf x_{i,\mathbf n}=\mathbf f_{i,\mathbf n}H+\mathbf o,
$$

where rows of $H$ are the instantaneous lattice vectors and $\mathbf o$ is the
frame origin.

# Fixed scientific face mapping

For every reference `TileFaceGeometry`, Stage 11B reconstructs the source ring
walk, face placement shift, tile-side attaching shift, and orientation. The
resulting ordered lifted references must replay the exact reference polygon
before frame coordinates are evaluated.

For Cartesian face vertices $\mathbf x_k$, define their arithmetic center

$$
\mathbf c_f=\frac{1}{n}\sum_{k=0}^{n-1}\mathbf x_k.
$$

The deterministic fan consists of triangles

$$
(\mathbf c_f,\mathbf x_k,\mathbf x_{k+1}).
$$

The stored face area is

$$
A_f
=
\frac12\sum_k
\left\|
(\mathbf x_k-\mathbf c_f)
\times
(\mathbf x_{k+1}-\mathbf c_f)
\right\|.
$$

Its area-weighted oriented vector determines the reported unit normal. Every fan
triangle must exceed the declared degeneracy tolerance.

## Planarity diagnostics

A best-fit plane is obtained from the least singular vector of the centered
vertex matrix. Stage 11B records

$$
\delta_{\mathrm{rms}}
=
\sqrt{\frac1n\sum_k d_k^2},
\qquad
\delta_{\max}=\max_k |d_k|,
$$

where $d_k$ is signed distance to the best-fit plane.

Vertices are projected into that plane. The reported aperture witness is the
minimum in-plane distance from the projected polygon center to its boundary
segments. `planar_aperture_certified` is true only when the projected polygon is
strictly convex, contains the witness, and $\delta_{\max}$ does not exceed the
configured planarity tolerance.

This flag certifies only the stored planar witness. It is not a maximum flexible
portal radius.

# Dynamic tile geometry

A mapped tile retains the source tile's ordered side indices. Unique lifted
vertex identities are gathered from all its sides.

A Cartesian reference point $\mathbf r$ is chosen as the arithmetic mean of the
unique tile vertices. Every oriented face-fan triangle
$(\mathbf c_f,\mathbf x_k,\mathbf x_{k+1})$ defines one signed tetrahedron:

$$
V_k
=
\frac16
(\mathbf c_f-\mathbf r)\cdot
\left[
(\mathbf x_k-\mathbf r)
\times
(\mathbf x_{k+1}-\mathbf r)
\right].
$$

The signed tile volume and volume centroid are

$$
V=\sum_k V_k,
\qquad
\mathbf c_V
=
\frac{1}{V}
\sum_k
V_k
\frac{\mathbf r+\mathbf c_f+\mathbf x_k+\mathbf x_{k+1}}{4}.
$$

A mapped tile is accepted only when orientation is preserved and $V>0$ beyond
tolerance. Derived descriptors are:

- absolute volume;
- surface area;
- equivalent-sphere radius;
- Wadell sphericity;
- maximum pairwise lifted-vertex distance; and
- Cartesian and fractional volume centroids.

The sum of all tile volumes must close to the instantaneous primitive-cell
volume within the configured absolute plus relative tolerance.

# Dynamic windows and adjacency

The scientific `TopologicalWindow` catalog remains unchanged. For each window,
the two mapped tile sides must agree geometrically after applying the stored
translation relation. Stage 11B reports:

- Cartesian window center;
- mean side area;
- side-area mismatch;
- minimum of the two projected aperture witnesses;
- maximum planarity RMS and maximum deviation; and
- a planar-aperture certificate only when both sides certify it.

Translation-labelled adjacency arcs are inherited unchanged from the reference
geometry. Stage 11B does not infer portal accessibility or crossing events.

# Persistent result model

## Per-frame status

```python
FrameTilingGeometryStatus(
    MAPPED,
    TOPOLOGY_MISMATCH,
    CONNECTIVITY_GEOMETRY_MISMATCH,
    DEGENERATE_GEOMETRY,
)
```

- `MAPPED`: complete face, window, and tile geometry with volume closure.
- `TOPOLOGY_MISMATCH`: exact projected graph differs from the certified source.
- `CONNECTIVITY_GEOMETRY_MISMATCH`: graph identity matches, but the declared
  atomic image gauge cannot be reconciled with frame geometry.
- `DEGENERATE_GEOMETRY`: the gauge maps, but a face/tile/window is degenerate,
  orientation reversing, geometrically inconsistent, or fails volume closure.

Unmapped frames contain no partial geometry.

## Main records

```python
FrameTileFaceGeometry(...)
FrameNaturalTileGeometry(...)
FrameWindowGeometry(...)
MappedTilingFrame(...)
FrameTilingGeometryCatalog(...)
```

`FrameTilingGeometryCatalog.tile_metric(tile_index, metric)` returns a
frame-aligned NumPy array and uses `NaN` for unresolved frames. Supported metrics
are

```text
volume
surface_area
equivalent_sphere_radius
sphericity
diameter
```

# Options and resources

```python
FrameTilingGeometryOptions(
    degeneracy_tolerance=1.0e-12,
    planarity_tolerance=1.0e-3,
    window_match_tolerance=1.0e-8,
    volume_closure_relative_tolerance=1.0e-8,
    volume_closure_absolute_tolerance=1.0e-8,
)
```

```python
FrameTilingGeometryResources(
    max_frames=100_000,
    max_vertices=100_000,
    max_tile_faces=1_000_000,
    max_vertex_instances=10_000_000,
    max_pair_distance_tests=100_000_000,
)
```

Frame count, framework vertices, tile sides, and total mapped face-vertex work are
preflighted before per-frame mapping begins. Tile diameter work is checked before
its pairwise distance loop. Resource failure never returns a partial persistent
catalog.

# Serialization and binding

The persistent catalog binds independently to:

- reference geometry;
- scientific periodic cell complex;
- authoritative embedding;
- primitive-ring catalog;
- topology catalog;
- selected collection geometry; and
- selected atomic-connectivity states.

Collection binding includes frame semantics, selected frame positions and IDs,
active atomic numbers, periodicity, cells, origins, and active fractional
coordinates. Connectivity binding includes the exact definition, resolved scope,
and selected state digests.

Loading is deterministic source replay:

```python
FrameTilingGeometryCatalog.from_dict(
    payload,
    reference_geometry=reference_geometry,
    complex_=complex_,
    embedding=embedding,
    ring_index=ring_index,
    collection=collection,
    connectivity=connectivity,
    topology_catalog=topology_catalog,
)
```

A payload is rejected when any stored field disagrees with the rebuilt result,
even when an outer digest is recomputed.

# Edge cases and failure policy

The first backend rejects or leaves explicit per-frame outcomes for:

- missing or non-unique selected frames;
- nonmonotonic trajectory frame selection;
- mismatched frame IDs or frame semantics;
- source digest disagreement;
- atom ordering incompatible with the source embedding;
- connectivity not using the unique-minimum-image convention;
- changed projected framework topology;
- a noninteger trajectory anchor reconciliation;
- inconsistent physical and canonical atomic edge images;
- degenerate boundary-center fan triangles;
- reversed or zero-volume tiles;
- inconsistent two-sided window geometry;
- failure of instantaneous cell-volume closure; and
- declared resource exhaustion.

The following remain outside Stage 11B:

- automatic atom correspondence between independently reordered structures;
- topology changes that require a new natural tiling;
- nonconvex or self-intersecting dynamic tile surfaces;
- explicit linker or van der Waals surfaces;
- chemistry-aware radius policies;
- maximum-clearance cage or portal searches;
- global free-volume connectivity;
- occupancy and portal-crossing event detection; and
- kinetic or energetic transport models.

# Focused validation requirements

The Stage-11B focused suite must cover:

1. full mapping of the real-LTA ten-tile scientific complex;
2. exact isotropic scaling of volumes, areas, and lengths;
3. invariance to independent integer atom wrapping;
4. whole-cell trajectory anchor continuity;
5. descriptive retention of thermally nonplanar faces;
6. explicit topology-mismatch frames and `NaN` metric alignment;
7. independent ensemble wrapping;
8. transactional resource preflight;
9. source replay and tamper rejection; and
10. wrong-source and unsupported-metric rejection.

# References

[1] S. J. Chung, T. Hahn, and W. E. Klee, "N-dimensional
crystallography," *Acta Crystallographica A* **40**, 42--50 (1984),
doi:10.1107/S010876738400010X.

[2] V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M.
Proserpio, "Three-periodic nets and tilings: natural tilings for nets,"
*Acta Crystallographica A* **63**, 418--425 (2007),
doi:10.1107/S0108767307038287.
