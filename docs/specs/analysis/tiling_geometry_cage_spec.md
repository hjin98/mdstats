---
title: "Natural-Tile Geometry and Cage Accessibility Specification"
subtitle: "Stage 11: Exact Reference Tiles, Topological Windows, Conservative Probe Witnesses, and Periodic Accessibility Networks"
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

Stage 11 begins the downstream physical interpretation branch after a certified
periodic natural tiling:

```text
accepted natural tiling
        -> exact reference tile geometry
        -> topological windows and translation-labelled adjacency
        -> explicit cage/portal probe witnesses
        -> periodic accessible-network rank
```

Runtime/API target:

```text
mdstats 0.19.28a0
```

Primary modules:

```text
mdstats/analysis/tiling_geometry.py
mdstats/analysis/cage.py
```

LTA integration helper:

```text
mdstats/analysis/lta_natural_tiling.py
    build_lta_natural_tiling_reference(...)
```

This first backend is deliberately bounded. It realizes the exact source-bound
reference embedding and requires strictly convex planar faces and convex tiles.
It certifies accessibility only at explicit witnesses under periodic spherical
obstacles. A blocked witness is **not** promoted to global inaccessibility.

# Scientific distinctions

The implementation preserves four separate concepts.

## Natural tile

A natural tile is a persistent topological 3-cell of the accepted periodic cell
complex. Its identity is determined by scientific faces and
translation-labelled attaching maps. Geometry does not redefine that identity.

## Topological window

A topological window is one scientific face orbit shared by exactly two translated
tile sides. It exists independently of guest size, atom radii, or instantaneous
aperture.

## Accessible cage

A natural tile becomes an accessible cage for a probe only when an explicit
interior witness clears every admitted periodic obstacle sphere by at least the
probe radius.

## Accessible portal

A topological window becomes an accessible portal only when one explicit
in-plane aperture witness:

1. contains a disk of the requested probe radius inside the convex polygon;
2. clears all periodic obstacle spheres by at least the probe radius; and
3. connects two tile placements whose cage witnesses are accessible.

These promotions are probe- and obstacle-model dependent. They never alter the
scientific natural tiling.

# External methods and original construction

The translation-labelled quotient convention follows Chung, Hahn, and Klee [1].
Natural-tile and properness semantics follow Blatov, Delgado-Friedrichs,
O'Keeffe, and Proserpio [2]. The stored sphericity descriptor is Wadell's true
sphericity, the equal-volume-sphere surface area divided by the tile surface area
[3].

The following mechanisms are project-specific `mdstats` constructions:

- exact lifted reconstruction of every tile-side polygon from scientific face
  placement plus attaching translation;
- exact convex supporting-halfspace validation against a rational interior
  witness;
- exact tetrahedral fan volume and first-moment accumulation in fractional
  coordinates;
- topological-window reconstruction directly from the two incidences of each
  scientific face orbit;
- complete nearest-periodic-image enumeration for a point witness using a
  metric-derived finite integer range, not a fixed image shell;
- conservative accessibility states that distinguish a sufficient witness from
  an unresolved blocked witness; and
- translation-rank classification of the accessible quotient network.

No external global pore-finding, Voronoi-network, or maximum-inscribed-sphere
algorithm is claimed or silently approximated.

# Inputs and source binding

## `build_tiling_geometry_catalog`

```python
build_tiling_geometry_catalog(
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    *,
    resources: TilingGeometryResources | None = None,
) -> TilingGeometryCatalog
```

Required source equalities are

```text
complex_.periodic_net_embedding_digest == embedding.digest
complex_.primitive_ring_catalog_digest == ring_index.catalog_digest
complex_.topology_graph_digest == ring_index.topology_graph_digest
```

The scientific complex must already satisfy the Stage-9 chain, shell, and
face-incidence invariants. The first geometry backend additionally requires:

- at least three vertices per face;
- exact planarity of each face polygon;
- strict polygon convexity;
- a convex tile supported by every oriented face plane;
- a strictly interior rational witness; and
- positive exact tile volume.

## `assess_cage_accessibility`

```python
assess_cage_accessibility(
    geometry: TilingGeometryCatalog,
    embedding: PeriodicNetEmbedding,
    probe: AccessibilityProbe,
    obstacles: Sequence[PeriodicObstacleSphere] = (),
    *,
    resources: CageAccessibilityResources | None = None,
) -> CageAccessibilityCatalog
```

All lengths use the Cartesian metric of the unit-volume reference embedding.
Obstacle coordinates are fractional and periodic. Obstacle and probe radii must
use the same Cartesian length unit.

# Persistent data model

## Tile geometry

```python
NaturalTileGeometry(
    tile_index: int,
    label: str,
    vertex_count: int,
    edge_count: int,
    face_count: int,
    side_indices: tuple[int, ...],
    fractional_center: tuple[Fraction, Fraction, Fraction],
    cartesian_center: tuple[float, float, float],
    fractional_volume: Fraction,
    cartesian_volume: float,
    surface_area: float,
    equivalent_sphere_radius: float,
    sphericity: float,
    diameter: float,
    convex_certified: bool,
)
```

`fractional_center` is the exact volume centroid of the convex tile, not merely
the arithmetic mean of vertices.

## Oriented tile sides

```python
TileSideRef(
    tile_index: int,
    face_index: int,
    face_image_shift: LatticeShift,
    incidence_orientation: Literal[-1, 1],
)
```

```python
TileFaceGeometry(
    side_index: int,
    side: TileSideRef,
    ring_size: int,
    fractional_vertices: tuple[RationalPoint, ...],
    fractional_center: RationalPoint,
    cartesian_center: tuple[float, float, float],
    outward_unit_normal: tuple[float, float, float],
    area: float,
    perimeter: float,
    aperture_witness_radius: float,
)
```

The face center is the equal-weight polygon-vertex average. For a strictly convex
polygon this point lies in the polygon interior and supplies a deterministic
aperture witness.

## Topological windows and adjacency

```python
TopologicalWindow(
    window_index: int,
    face_index: int,
    face_digest: str,
    ring_size: int,
    side_a: TileSideRef,
    side_b: TileSideRef,
    relative_tile_translation: LatticeShift,
    self_adjacent: bool,
    area: float,
    aperture_witness_radius: float,
    fractional_center: RationalPoint,
    cartesian_center: tuple[float, float, float],
)
```

```python
TileAdjacencyArc(
    arc_index: int,
    window_index: int,
    source_tile_index: int,
    target_tile_index: int,
    target_image_shift: LatticeShift,
)
```

Each window produces two reverse directed arcs. Self-image adjacency is retained
as a tile orbit connected to a nonzero translated image of itself.

## Probe and obstacle model

```python
AccessibilityProbe(radius: float, label: str = "probe")
```

```python
PeriodicObstacleSphere(
    obstacle_id: int,
    fractional_coordinate: RationalPoint,
    radius: float,
    label: str = "",
)
```

The obstacle model is explicit evidence. The module does not infer van der Waals,
ionic, or framework radii from chemical species.

## Accessibility states

```python
WitnessAccessibilityStatus.CERTIFIED_ACCESSIBLE_AT_WITNESS
WitnessAccessibilityStatus.WITNESS_BLOCKED_UNRESOLVED
```

The second state means only that the stored deterministic witness failed. Another
point, a nonspherical path, or a more complete geometric search may still prove
accessibility.

# Exact tile realization

For one tile orbit, each attaching term supplies a translated face placement.
The exact lifted polygon is

$$
P_{f,\mathbf t}
=
\{\mathbf x_i+\mathbf t\}_{i=0}^{m-1}.
$$

The union of exact polygon vertices supplies a provisional rational interior
point

$$
\mathbf c_0=\frac{1}{N}\sum_{i=1}^{N}\mathbf v_i.
$$

For a convex full-dimensional polytope, a positive average over all vertices lies
in its interior. Each face plane is oriented so that

$$
\mathbf n_f\cdot(\mathbf c_0-\mathbf p_f)<0.
$$

The backend then requires every tile vertex to satisfy

$$
\mathbf n_f\cdot(\mathbf v-\mathbf p_f)\le 0
$$

for every face. All tests use exact rational signs in fractional coordinates.

# Volume and centroid

Each outward-oriented convex face polygon is triangulated as a boundary fan. For
one triangle $(\mathbf a,\mathbf b,\mathbf c)$ and interior point $\mathbf c_0$,
its tetrahedral volume is

$$
V_t=\frac{1}{6}
\left|
\det(
\mathbf a-\mathbf c_0,
\mathbf b-\mathbf c_0,
\mathbf c-\mathbf c_0)
\right|.
$$

The tile volume is

$$
V=\sum_t V_t,
$$

and the exact first moment is

$$
V\mathbf c
=
\sum_t V_t
\frac{\mathbf c_0+\mathbf a_t+\mathbf b_t+\mathbf c_t}{4}.
$$

The reference embedding has unit Cartesian cell volume, so exact fractional tile
volume equals Cartesian volume numerically.

# Surface descriptors

For Cartesian volume $V$ and surface area $A$, the equal-volume sphere radius is

$$
r_{\mathrm{eq}}
=
\left(\frac{3V}{4\pi}\right)^{1/3}.
$$

Wadell sphericity is

$$
\Psi
=
\frac{\pi^{1/3}(6V)^{2/3}}{A}.
$$

The diameter is the largest Cartesian distance between tile vertices. These are
derived descriptors; they do not enter tile identity or natural-tiling
certification.

# Window translation and adjacency

Suppose the two tile representatives contain face $f$ at attaching shifts
$\mathbf s_a$ and $\mathbf s_b$. Aligning the same physical face requires the
second tile image

$$
\mathbf T_{a\rightarrow b}
=
\mathbf s_a-\mathbf s_b.
$$

The reverse arc stores $-\mathbf T_{a\rightarrow b}$. A self-adjacent tile orbit
with nonzero $\mathbf T$ is therefore represented without collapsing periodic
connectivity.

# Aperture witness

For one strictly convex face polygon, let $\mathbf q$ be the Cartesian image of
the equal-weight vertex average. The stored geometric witness radius is

$$
r_{\mathrm{poly}}(\mathbf q)
=
\min_{e\in\partial P}
\operatorname{dist}(\mathbf q,e).
$$

This certifies that a planar disk of radius $r_{\mathrm{poly}}$ centered at
$\mathbf q$ is contained in the polygon. It is not claimed to be the maximum
inscribed circle unless symmetry makes it so.

# Complete nearest periodic obstacle search

For witness fractional coordinate $\mathbf q$, obstacle coordinate $\mathbf x$,
integer image $\mathbf n$, and row-cell matrix $H$, the center distance is

$$
d(\mathbf n)=\| (\mathbf q-\mathbf x+\mathbf n)H\|_2.
$$

A componentwise rounded image supplies an initial finite upper bound $R$. Since

$$
\mathbf y=(\mathbf q-\mathbf x+\mathbf n)
=((\mathbf q-\mathbf x+\mathbf n)H)H^{-1},
$$

Cauchy--Schwarz gives the finite component bounds

$$
|y_i|
\le
R\,\|(H^{-1})_{:,i}\|_2.
$$

The backend enumerates every integer image in those metric-derived ranges and
therefore does not assume a fixed $3\times3\times3$ image shell.

Obstacle-surface clearance is

$$
\delta
=
\min_j\left(d_j-r_j\right).
$$

A probe of radius $r_p$ is certified at the witness when

$$
\delta\ge r_p.
$$

For portals the polygon witness also requires

$$
r_{\mathrm{poly}}\ge r_p.
$$

# Accessible-network rank

Only arcs whose portal witness and both endpoint cage witnesses are certified are
retained. A spanning forest assigns image potentials $\mathbf p_i$ to tile
orbits. Every non-tree arc $i\rightarrow j$ with translation $\mathbf t_{ij}$
produces a cycle voltage

$$
\mathbf z
=
\mathbf p_i+\mathbf t_{ij}-\mathbf p_j.
$$

The rational rank of the nonzero voltage vectors classifies the periodic
accessible component:

| Rank | Interpretation |
|---:|---|
| 0 | isolated cage |
| 1 | one-dimensional channel |
| 2 | two-dimensional layer |
| 3 | three-dimensional network |

This is a topological periodic-rank statement for the certified witness graph,
not a diffusion-rate or energetic-transport prediction.

# LTA integration

`build_lta_natural_tiling_reference(topology)` reruns the exact Stage-10D
$K=8$ construction and returns transient source objects:

```python
LtaNaturalTilingReference(
    view,
    discovery,
    embedding,
    ring_index,
    complex,
    partition,
)
```

It creates no second persistent tiling identity. The returned complex and ring
index can be passed directly to `build_tiling_geometry_catalog`.

The real-LTA gate must recover:

```text
10 tiles
58 topological windows
116 directed adjacency arcs
exact total fractional volume = 1
6 [4^6] tiles
2 [4^6.6^8] tiles
2 [4^12.6^8.8^6] tiles
```

# Resource limits

## Geometry

```python
TilingGeometryResources(
    max_tiles=4096,
    max_faces=16384,
    max_vertices_per_face=128,
    max_pair_distance_tests=5_000_000,
)
```

## Accessibility

```python
CageAccessibilityResources(
    max_obstacles=100_000,
    max_periodic_image_tests=5_000_000,
    max_network_arcs=1_000_000,
)
```

Resource failures occur before the declared bound is exceeded and never return a
partial persistent catalog.

# Serialization and reproducibility

Both catalogs use deterministic canonical JSON and SHA-256 digests. Persistent
loading is source replay:

```python
TilingGeometryCatalog.from_dict(
    payload,
    complex_=complex_,
    embedding=embedding,
    ring_index=ring_index,
)
```

```python
CageAccessibilityCatalog.from_dict(
    payload,
    geometry=geometry,
    embedding=embedding,
)
```

A payload with a recomputed outer digest is still rejected when any geometric or
accessibility field disagrees with deterministic reconstruction.

# Edge cases and failure policy

The first backend rejects or leaves unresolved:

- nonplanar, degenerate, or non-strictly-convex scientific faces;
- nonconvex tile shells;
- source-digest mismatches;
- inconsistent translated face areas or aperture witnesses;
- more or fewer than two tile sides per scientific face;
- malformed obstacle IDs or nonfinite radii;
- resource exhaustion;
- blocked cage or portal witnesses, which remain unresolved globally;
- frame-dependent chemical geometry not represented by the reference embedding;
- nonspherical guests or obstacles;
- flexible-window path search;
- maximum-inscribed-sphere or full pore-network optimization;
- automatic radii assignment from species; and
- transport kinetics or free-energy barriers.

# Focused validation requirements

The Stage-11 focused suite must cover:

1. exact unit-cube volume, centroid, surface area, edges, and diameter;
2. self-image topological windows and reverse translation arcs;
3. rank-three obstacle-free accessible cube network;
4. a probe larger than the stored portal witness;
5. periodic obstacle images at a cell boundary;
6. a blocked cage witness without a false global-inaccessibility claim;
7. transactional resource preflight;
8. deterministic replay and tamper rejection;
9. source-type rejection; and
10. the real-LTA 10-tile, 58-window, unit-volume ground gate.

# Deferred extensions

The next implementation rounds may add:

- geometry mapped onto arbitrary compatible trajectory or ensemble frames;
- explicit linker-atom and van der Waals surfaces;
- automatic chemistry-aware radius policies;
- maximum-clearance points and flexible portal paths;
- nonconvex tile decomposition;
- guest-specific connected free-volume regions;
- cage occupancy and portal-crossing events over trajectories; and
- coupling to diffusion and residence-time statistics.

# References

[1] S. J. Chung, T. Hahn, and W. E. Klee, "N-dimensional
crystallography," *Acta Crystallographica A* **40**, 42--50 (1984),
doi:10.1107/S010876738400010X.

[2] V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M.
Proserpio, "Three-periodic nets and tilings: natural tilings for nets,"
*Acta Crystallographica A* **63**, 418--425 (2007),
doi:10.1107/S0108767307038287.

[3] H. Wadell, "Volume, shape, and roundness of quartz particles," *The
Journal of Geology* **43**, 250--280 (1935), doi:10.1086/624298.
