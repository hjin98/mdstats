# Registered structural geometry view specification

## Status

- Owner: Stage C0A3 registered structural-view integration
- Release target: `mdstats 0.19.95a0`
- Upstream contracts: C0A1 source-coordinate semantics and lattice gauge, C0A2 affine registration, Stage 11C1/C2 ring and tiling geometry, Stage 11C3 atom-resolved ring boundaries
- Downstream consumers: statistical-site association, registered density interpretation, structural classification, and visualization

## Purpose

A site-density field and an instantaneous framework geometry may inhabit different Cartesian coordinate measures. The package therefore requires one immutable, source-bound object that links:

1. the **physical structural geometry**, used for bond lengths, apertures, areas, volumes, and coordination; and
2. the **registered structural embedding**, used for density-space displacement and structural association.

The view must never silently replace physical geometry with registered geometry or mix coordinates from the two representations.

## Scope

C0A3 provides:

- framewise application of one resolved `FrameRegistrationResult` to persistent T and O ring atoms;
- registered ring, window, tile, and natural-tile/cage centers;
- registered tile-face vertices when a frame tiling catalog is supplied;
- reconstruction of orthonormal registered ring frames from transformed atom coordinates;
- explicit physical and registered geometry records linked by persistent atom and structural identities;
- periodic image reconstruction in the registered cell;
- trajectory-only orientation-continuity diagnostics with registration segment resets;
- deterministic serialization, replay, signatures, resource preflight, and fail-closed source validation.

C0A3 does **not**:

- discover statistical sites;
- compute M--O or M--T coordination fingerprints;
- modify C1/C2/C3 physical geometry;
- migrate MSD, density, or plotting consumers;
- infer temporal continuity for independent ensembles; or
- convert registered geometric sizes into physical bond or aperture claims.

## Coordinate convention

Row-vector coordinates are retained. For frame $t$, the resolved registration map is

$$
\mathbf q = \mathbf x M_t + \mathbf b_t,
\qquad
G_t = H_t M_t,
$$

where $\mathbf x$ is a physical Cartesian point, $H_t$ is the physical cell in the resolved lattice gauge, $\mathbf q$ is the registered Cartesian point, and $G_t$ is the registered cell.

Every transformed structural point is produced by the exact C0A2 map. A ring atom with persistent source reference

$$
(a,\mathbf n),\qquad \mathbf n\in\mathbb Z^3,
$$

is validated against the registered base atom and decomposed as

$$
\mathbf q_{a,\mathbf n}
=
\mathbf q_a + \mathbf m G_t,
\qquad \mathbf m\in\mathbb Z^3.
$$

The integer registered image $\mathbf m$ is solved and certified from the transformed coordinates. It is not assumed to equal the source image label when the source lattice basis has been reconciled by a unimodular gauge.

## Separation of physical and registered geometry

A `RegisteredRingStructuralView` contains two explicit children.

```text
PhysicalRingGeometrySnapshot
    physical T/O coordinates
    physical center and orthonormal frame
    physical aperture, area, perimeter, planarity, and T--O distances

RegisteredRingEmbedding
    transformed T/O coordinates and registered images
    reconstructed registered center and orthonormal frame
    registered projected descriptors for association only
```

No generic `center`, `distance`, or `aperture` field is exposed at the combined level. Consumers must select `physical` or `registered` explicitly.

Physical values are copied without numerical reinterpretation from the compatible C2 frame geometry. Registered projected sizes are separately named and must not be reported as physical coordination geometry.

## Registered atom embedding

Each persistent T/O atom record retains:

- boundary kind and cyclic index;
- `RingAtomRef` source atom and image identity;
- element and Stage 11C3 chemical/environment annotations;
- physical Cartesian coordinates;
- registered Cartesian coordinates;
- registered unwrapped and wrapped fractional coordinates;
- registered integer image shift relative to the transformed base atom; and
- a periodic-image residual.

The transformed atom must agree with the registered base atom plus an integer registered-cell translation within `coordinate_tolerance`. A disagreement is a source-binding error, not a recoverable ring deformation.

## Registered ring-frame reconstruction

A non-rigid affine map does not preserve orthogonality. Therefore a registered local frame is reconstructed from transformed atoms; physical frame axes are never merely multiplied by $M_t$ and relabeled orthonormal.

For transformed ordered oxygen coordinates $\mathbf q_j$:

1. compute the covariance about the vertex centroid;
2. take the least-variance eigenvector as a provisional plane normal;
3. sign the normal by the ordered polygon vector area;
4. project the polygon and compute its signed area centroid;
5. choose the in-plane $\hat{\mathbf u}$ axis from the projected persistent cyclic-origin atom;
6. set
   $$
   \hat{\mathbf v}=\hat{\mathbf n}\times\hat{\mathbf u};
   $$
7. verify unit length, mutual orthogonality, positive ordered area, and non-singular projected origin radius.

The reconstructed frame stores:

- center and orthonormal axes;
- covariance eigenvalues;
- projected area, perimeter, aperture witness, and planarity diagnostics;
- minimum projected atom radius;
- orthonormality error;
- transformed-physical-axis non-orthogonality diagnostic; and
- displacement between the reconstructed center and the directly transformed physical center.

The transformed physical axes may be retained only as a diagnostic. They are not the registered orthonormal frame.

## Orientation continuity

Persistent atom order fixes the frame gauge independently in every frame. For a trajectory, consecutive resolved frames also record

$$
c_n(t)=\hat{\mathbf n}_{t-1}\cdot\hat{\mathbf n}_t,
\qquad
c_u(t)=\hat{\mathbf u}_{t-1}\cdot\hat{\mathbf u}_t.
$$

No continuity comparison is made:

- at the first selected frame;
- across a C0A2 `segment_reset_frame_indices` boundary; or
- for `FrameSemantics.ENSEMBLE`.

When enabled, a continuity dot below the declared threshold makes that ring view unresolved and records the failure. No sign flip is applied to hide the discontinuity.

## Tile, face, window, and cage embeddings

When a compatible `FrameTilingGeometryCatalog` is supplied, the view additionally records:

- natural-tile centers, explicitly designated as tile/cage centers;
- physical tile volume, surface area, diameter, sphericity, and orientation status unchanged;
- registered tile/cage center coordinates and periodic image data;
- transformed tile-face vertices and reconstructed face normals; and
- registered window centers linked to unchanged physical aperture and area metrics.

The natural tile is the current persistent cage-like structural unit. C0A3 does not assign a chemical cage name or a statistical-site identity.

## Status model

A frame is `resolved`, `partial`, or `unresolved`.

A ring view may be unresolved because:

- the C2 frame ring is unresolved;
- the C3 boundary is unresolved;
- C2 and C3 persistent identities disagree;
- transformed atom images cannot be certified;
- the transformed polygon is degenerate;
- the cyclic-origin direction is singular; or
- required trajectory orientation continuity fails.

Unresolved rings retain identity and a diagnostic but no partial registered geometry. Physical source geometry remains available through the upstream C2/C3 objects and their digests.

A missing or unresolved optional tiling frame does not erase valid ring views; it makes the frame `partial` and records a tiling diagnostic.

## Source binding and invariants

Construction fails before output when:

- frame indices or frame IDs disagree across C2, C3, registration, and the collection;
- the C3 catalog is not bound to the supplied C2 catalog;
- an optional tiling catalog contains duplicate or incompatible frame indices;
- a boundary atom identity or physical coordinate disagrees with C2 geometry;
- a transformed image does not close on the registered lattice; or
- resource estimates exceed the declared limits.

For every resolved ring:

- T/O identity order matches Stage 11C3 exactly;
- physical C2 metrics are retained exactly;
- the registered frame is right-handed and orthonormal;
- registered atom coordinates are exact C0A2 transforms;
- wrapped coordinate plus image shift reconstructs the registered coordinate; and
- no registered descriptor is used to overwrite a physical descriptor.

## Method provenance

The covariance-eigenvector best-fit plane follows the classical least-squares
closest-plane construction introduced by Pearson [C0A3-1]. The implementation
adapts that standard construction to an ordered periodic oxygen polygon, then
uses the polygon's oriented vector area and its projected shoelace centroid as
standard computational-geometry operations [C0A3-2]. The following parts are
project-specific constructions rather than borrowed algorithms:

- the strict separation between physical and registered structural records;
- exact C0A2 affine-map application to persistent atom/image identities;
- independent certification of registered periodic images;
- reconstruction from transformed atoms instead of affine axis propagation;
- trajectory-segment orientation diagnostics; and
- source-bound canonical replay and resource contracts.

## Public API

```python
build_registered_structural_geometry_view(
    collection,
    registration,
    frame_ring_geometry,
    ring_boundaries,
    *,
    frame_tiling_geometry=None,
    options=None,
    resources=None,
) -> RegisteredStructuralGeometryView
```

Primary persistent records:

```text
LinkedStructuralAtomEmbedding
PhysicalRingGeometrySnapshot
RegisteredOrthonormalRingFrame
RegisteredRingEmbedding
RegisteredRingStructuralView
RegisteredTileCageEmbedding
RegisteredTileFaceEmbedding
RegisteredWindowEmbedding
RegisteredStructuralFrameView
RegisteredStructuralGeometryView
```

## Serialization and signatures

The canonical schema is `mdstats.registered-structural-geometry-view.v1`.

The view digest binds:

- collection geometry/identity digest;
- registration signature;
- C2 frame-ring digest;
- C3 ring-boundary digest;
- optional frame-tiling digest;
- options and resources;
- all frame statuses, linked atom identities, physical snapshots, registered embeddings, and diagnostics.

`from_dict` performs source replay and requires byte-for-byte canonical payload equality. A modified payload, a changed source object, or a different registration result is rejected.

## Resource preflight

Before transforming coordinates, construction checks upper bounds on:

- frames;
- ring instances;
- linked T/O atom instances;
- tile instances;
- tile-face vertex instances; and
- window instances.

No partial catalog is returned after a resource failure.

## Acceptance tests

C0A3 is accepted when focused tests demonstrate:

1. identity registration reproduces registered T/O coordinates exactly while retaining all C3 identities;
2. a non-rigid shear/strain yields an orthonormal reconstructed frame even when affinely transformed physical axes are non-orthogonal;
3. physical bond lengths and aperture metrics remain byte-for-byte/numerically unchanged;
4. transformed ring atoms crossing periodic boundaries receive certified registered image shifts;
5. trajectory orientation checks honor segment resets and are skipped for ensembles;
6. unresolved C2/C3 rings remain explicit without partial registered records;
7. optional tile/cage, face, and window embeddings transform centers and vertices without overwriting physical metrics;
8. source mismatch, resource overflow, and serialization tampering fail closed; and
9. public analysis and root-package exports are stable.

## Next boundary

After C0A3, the next implementation stage is **C0B consumer migration**. Existing MSD, density, and plotting consumers are not migrated in this release.

## References

[C0A3-1] Pearson, K. (1901). *On Lines and Planes of Closest Fit to Systems
of Points in Space*. Philosophical Magazine, Series 6, 2(11), 559--572. DOI:
[10.1080/14786440109462720](https://doi.org/10.1080/14786440109462720).

[C0A3-2] O'Rourke, J. (1998). *Computational Geometry in C*, 2nd edition.
Cambridge University Press.
