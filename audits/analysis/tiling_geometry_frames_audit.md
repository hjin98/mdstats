# Stage 11B Compatible-Frame Natural-Tile Geometry Audit

Release target: `mdstats 0.19.29a0`

## Scope

Stage 11B adds `tiling_geometry_frames.py`. The module maps one certified
Stage-9/10 natural tiling and its Stage-11 reference geometry onto selected frames
of an `AtomisticFrameCollection` when the exact projected framework graph remains
compatible.

The implementation is descriptive. It does not rediscover rings, choose new
faces, rebuild a natural tiling, or infer accessibility.

## Source contract

The mapper requires mutually consistent:

- `TilingGeometryCatalog`;
- `PeriodicCellComplex`;
- `PeriodicNetEmbedding`;
- `PrimitiveRingIndex`;
- atomistic collection;
- source-bound `AtomicConnectivityResult`; and
- `TopologyCatalog` with the framework mapping used for projection.

Reference geometry, complex, embedding, ring catalog, topology graph, frame
semantics, frame IDs, periodicity, and framework vertex atom ordering are checked
before mapping. The connectivity result must declare the unique-minimum-image
atomic edge convention.

## Periodic gauge replay

The implementation reconstructs the same canonical periodic placement used by
the existing topology pipeline:

1. physical atomic minimum-image shifts are recomputed from wrapped frame
   coordinates;
2. their difference from canonical atomic-state shifts yields the atomic image
   gauge;
3. relevant-subgraph normalization is replayed from atomic paths;
4. final projected-framework normalization is replayed from framework edges; and
5. a global integer shift aligns a trajectory anchor with its unwrapped
   coordinate or independently wraps an ensemble anchor.

The projected framework is never assigned a nearest image by a new heuristic.
Real-LTA development checks recovered all canonical projected edge displacements
to approximately `4.3e-15` in fractional-coordinate norm.

## Dynamic surfaces and volumes

Every tile side is reconstructed from the persistent source ring walk, face
placement, attaching translation, and orientation. Dynamic faces may be
nonplanar. They are retained with one deterministic boundary-center fan and store:

- fractional and Cartesian vertices and center;
- fan area and area-weighted normal;
- perimeter;
- best-fit-plane RMS and maximum deviations;
- projected center-to-boundary aperture witness; and
- a conservative planar-aperture flag.

Mapped tiles retain their scientific side list and label. Oriented face-fan
tetrahedra provide signed volume and first moment. The backend rejects orientation
reversal, zero/negative volume, inconsistent lifted vertices, inconsistent two-
sided windows, and failure of instantaneous cell-volume closure.

## Explicit per-frame outcomes

The persistent frame state is one of:

```text
MAPPED
TOPOLOGY_MISMATCH
CONNECTIVITY_GEOMETRY_MISMATCH
DEGENERATE_GEOMETRY
```

Unmapped frames contain no partial tile, face, or window geometry. Frame-aligned
tile-metric accessors preserve those positions as `NaN`.

## Persistence and resources

`FrameTilingGeometryCatalog` binds separately to the scientific reference,
selected collection geometry, selected connectivity states, and topology catalog.
Canonical loading reruns the complete mapping and rejects tampering.

Transactional controls cover frame count, framework vertices, tile sides, total
face-vertex instances, and tile-diameter pair tests.

## LTA validation

The real Na-LTA fixture maps:

```text
10 natural tiles
116 oriented tile sides
58 topological windows
exact projected topology graph match
instantaneous tile-volume sum = cell volume
```

A uniform cell scale `s` gives the expected descriptor scaling:

```text
volume       -> s^3
area         -> s^2
length       -> s
```

Independent integer atom wrapping preserves intrinsic geometry. A whole-cell
trajectory crossing changes only the global image placement. Removing one source
atomic edge produces an explicit topology-mismatch frame and a `NaN` in the
aligned metric series.

## External provenance

- translation-labelled periodic quotient semantics: Chung, Hahn, and Klee
  (1984), DOI `10.1107/S010876738400010X`;
- natural-tile identity: Blatov, Delgado-Friedrichs, O'Keeffe, and Proserpio
  (2007), DOI `10.1107/S0108767307038287`.

Gauge composition, compatible-frame source binding, nonplanar fan mapping,
per-frame outcome separation, and replay persistence are current `mdstats`
constructions. Singular-value best-fit plane diagnostics are standard numerical
linear algebra background.

## Deliberate limitations

Stage 11B does not provide:

- atom correspondence for reordered structures;
- tiling identity across topology changes;
- self-intersection certification for arbitrary severely distorted dynamic
  surfaces;
- explicit linker/van der Waals surfaces;
- chemical radius policies;
- maximum-clearance or flexible-path portal searches;
- global free-volume connectivity;
- occupancy or crossing event detection; or
- kinetic or energetic transport inference.
