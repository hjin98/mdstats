# Stage 10D LTA Natural-Tiling Gate Implementation Audit

Release target: `mdstats 0.19.27a0`

## Implemented scientific boundary

`mdstats.analysis.lta_natural_tiling` implements an exact LTA-specific ground
backend rather than a generic automatic natural-tiling constructor.

The public entry point

```python
certify_lta_natural_tiling(topology, bounds=(8, 10, 12), resources=None)
```

requires the unlabeled connected rank-three, index-one LTA quotient with 48
vertices, 96 edges, degree four, and a complete exact automorphism group of order
96.

For every requested bound it independently rebuilds the primitive-ring catalog,
source-bound index, depth-one bounded-strength catalog, and exact rational polygon
classification. The full downstream face/complex/partition certificate is built
at `K=8`. At `K=10` and `K=12`, that evidence is reused only after the newly
rebuilt source stages prove exact equality of the ordered selected-ring stable
keys.

## Exact face decision

A ring is selected only when it is both:

```text
STRONG_IN_DOMAIN
STRICTLY_CONVEX_PLANAR
```

The exact determinant/projection test produces:

```text
K=8:  36 x 4R, 16 x 6R, 6 x 8R selected
K=10: 36 x 4R, 16 x 6R, 6 x 8R selected
K=12: 36 x 4R, 16 x 6R, 6 x 8R selected
       32 x strong 12R explicitly excluded as nonplanar
```

Every selected polygon receives one canonical convex fan witness. Direct exact
periodic triangle tests reject forbidden self-images, and direct exact
framework-segment/triangle tests retain only boundary-edge and shared-vertex
contacts permitted by Stage 8C.

## Tile reconstruction

Every framework edge has exactly three incident selected face placements. Their
exact face-interior rays are sorted in a rational quotient plane normal to the
edge. Consecutive sectors produce oriented face-side adjacencies with explicit
lattice gains. Translation propagation yields ten zero-gain finite components.
A nonzero gain cycle is a hard rejection of a slab, channel, or other noncompact
candidate.

Stage 9 validates the resulting translation-labelled complex:

```text
cell counts: (48, 96, 58, 10)
chain identities: passed
Euler characteristic: 0
face-side incidence: exactly two per face orbit
all tile shells: connected, nonbranching, orientable, genus zero
```

Recovered tile multiplicities:

```text
6 x [4^6]
2 x [4^6.6^8]
2 x [4^12.6^8.8^6]
```

The reduced ratio is `3:1:1`.

## Properness

The complete discovery supplies five exact generators. Stage 10D independently
replays multiplication-table closure and recovers all 96 operations. Each
generator maps every scientific face and translation-labelled tile shell inside
the same complex. Because the certified generators generate the complete group,
all net automorphisms preserve the tiling.

The implementation records 3,800 closure/image checks per bound observation.
Auxiliary fan triangles and convex-partition records are excluded from the
scientific action.

## Convex periodic partition

For every lifted tile, the implementation verifies all vertices against all
outward supporting face halfspaces. The exact average of distinct vertices is a
strict interior witness.

Exact fractional volumes are:

```text
6 x 1/256
2 x 61/768
2 x 157/384
sum = 1
```

Periodic AABB overlap ranges produce 122 tile-image pair candidates. The exact
convex-polytope separating-axis family uses face normals and edge-direction cross
products. The LTA fixture requires 564 tested canonical axes and proves pairwise
periodic interior-disjointness. Convexity, disjoint interiors, and total volume
one certify no positive-volume void in the primitive three-torus.

## Persistence and resources

The persistent result separates:

- source digests;
- per-bound ring, strength, and geometry summaries;
- selected and excluded stable ring-key digests;
- mesh-independent scientific complex keys;
- exact partition summaries;
- properness summaries; and
- aggregate certification state.

Canonical JSON and SHA-256 protect the result. `from_dict()` replays the complete
gate against the supplied topology. Transactional resources bound all finite
search and exact-test dimensions.

## Deliberate limitations

The implementation does not claim:

- a generic natural-face or master-refinement constructor;
- arbitrary periodic-net recognition up to unrestricted change of cell/basis;
- nonplanar face-surface search;
- alternative witness enumeration;
- stabilization for all `K > 12`; or
- physical cage/accessibility semantics.

These limitations are stated in code and in the Stage-10D specification.
