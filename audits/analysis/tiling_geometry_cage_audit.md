# Stage 11 Tile Geometry and Cage Accessibility Audit

Release target: `mdstats 0.19.28a0`

## Scope

Stage 11 adds the first downstream interpretation backend after a certified
periodic natural tiling. The implementation is split deliberately:

- `tiling_geometry.py` owns exact source-bound reference geometry, topological
  windows, and translation-labelled tile adjacency;
- `cage.py` owns probe-dependent cage/portal witness assessments and accessible
  network rank; and
- `lta_natural_tiling.py` exposes a transient exact LTA source bundle for the
  downstream branch without creating a second persistent natural-tiling result.

## Implemented invariants

### Reference tile geometry

- cell-complex, embedding, ring-index, and topology digests must agree;
- every scientific face is reconstructed from its persistent ring placement and
  attaching translation;
- every face is exactly planar and strictly convex;
- one rational vertex-average witness lies strictly inside every supporting
  face halfspace;
- every tile is convex under those exact supporting planes;
- face fan tetrahedra are nondegenerate;
- exact fractional volumes are positive;
- exact first moments produce the stored rational volume centroids;
- each scientific face orbit has exactly two opposite tile-side incidences;
- translated copies of one interface have equal area and aperture witnesses;
- every window produces two reverse directed adjacency arcs; and
- self-image tile adjacency retains its nonzero lattice translation.

### Accessibility

- obstacle IDs are dense, ordered, periodic sphere orbits;
- probe and obstacle radii are finite and nonnegative;
- the geometry and embedding digests agree;
- nearest periodic obstacle images are enumerated through metric-derived finite
  bounds, not a fixed image shell;
- accessible cage and portal results are sufficient witness certificates only;
- a blocked witness remains `WITNESS_BLOCKED_UNRESOLVED`;
- a portal is promoted only when its polygon witness, obstacle clearance, and
  both adjacent cage witnesses admit the probe;
- only certified arcs enter the accessible quotient network; and
- exact rational cycle-voltage rank classifies isolated, 1D, 2D, or 3D
  accessible components.

## Geometry outputs

For each tile, the backend stores exact fractional volume and centroid plus
Cartesian surface area, diameter, equal-volume-sphere radius, and Wadell
sphericity. For each tile side it stores the exact lifted polygon, center,
outward normal, area, perimeter, and deterministic contained-disk witness radius.

These descriptors do not alter scientific tile or face identity.

## LTA integration

`build_lta_natural_tiling_reference()` reruns the Stage-10D K=8 construction and
returns the exact view, complete symmetry discovery, authoritative embedding,
primitive-ring index, periodic cell complex, and convex partition certificate.
The Stage-11 real-LTA test recovers:

```text
10 tiles
58 topological windows
116 directed adjacency arcs
exact total fractional volume = 1
6 [4^6] tiles
2 [4^6.6^8] tiles
2 [4^12.6^8.8^6] tiles
```

The exact tile volumes agree with the Stage-10D partition certificate.

## Persistence

`TilingGeometryCatalog` and `CageAccessibilityCatalog` use canonical JSON and
SHA-256 digests. `from_dict()` performs deterministic reconstruction from the
owning scientific sources and rejects modified geometric or accessibility fields,
even when the caller supplies an otherwise well-formed payload.

## External provenance

- translation-labelled periodic quotient semantics: Chung, Hahn, and Klee
  (1984), DOI `10.1107/S010876738400010X`;
- natural-tile semantics: Blatov, Delgado-Friedrichs, O'Keeffe, and Proserpio
  (2007), DOI `10.1107/S0108767307038287`;
- sphericity descriptor: Wadell (1935), DOI `10.1086/624298`.

Exact convex reconstruction, metric-derived periodic witness search, conservative
promotion states, and cycle-voltage accessibility classification are the present
`mdstats` constructions.

## Deliberate limitations

The first backend is restricted to:

- the exact unit-volume reference embedding;
- strictly convex planar faces and convex tiles;
- explicit spherical probe and obstacle models;
- one deterministic cage witness and one deterministic portal witness; and
- sufficient accessibility certificates rather than global pore exclusion.

It does not yet map geometry onto arbitrary trajectory frames, infer linker-atom
surfaces or chemical radii, optimize maximum-clearance points, search flexible or
nonspherical paths, decompose nonconvex tiles, or infer occupancy and portal
crossings over time.
