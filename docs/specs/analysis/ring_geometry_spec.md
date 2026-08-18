---
title: "Reference Oxygen-Ring Geometry Specification"
subtitle: "Stage 11C1: Persistent T/O Polygons, Geometric Centers, and Two-Sided Local Frames"
author: "mdstats"
date: "2026-07-23"
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

Stage 11C1 binds every certified natural-tiling window to one atomistic
reference-frame realization of its projected T ring and bridging-oxygen ring:

```text
certified natural tiling + primitive-ring index + framework topology
        + one atomistic reference frame + compatible atomic connectivity
        -> persistent lifted T polygon
        -> exact one-oxygen-per-edge O polygon
        -> oxygen-ring geometric centers and best-fit plane
        -> two oriented ring-side local frames
        -> immutable source-bound geometry catalog
```

Runtime/API target:

```text
mdstats 0.19.87a0
```

Primary module:

```text
mdstats/analysis/ring_geometry.py
```

Stage 11C1 is a structural and descriptive geometry layer. It does **not**
construct physical ionic sites, infer free-energy minima, label LTA cages, map
geometry over a trajectory, or assign ions to states. Stage 11C2 will map these
fixed identities over compatible frames.

# Scientific distinctions

The implementation keeps the following objects separate:

- the natural-tiling T-face center, obtained from projected framework vertices;
- the O-ring vertex centroid;
- the O-ring projected-area centroid, used as the default geometric ring center;
- a later probe-dependent maximum-clearance center; and
- a later species-dependent metastable-site center.

Consequently,

$$
\mathbf c_{\mathrm{T-face}}
\ne
\mathbf c_{\mathrm O,v}
\ne
\mathbf c_{\mathrm O,A}
\ne
\mathbf c_{\mathrm{clear}}^M
\ne
\mathbf c_{\mathrm{site}}^M
$$

in general. Equality in a high-symmetry case does not collapse their meanings.

# External methods and original construction

Least-squares plane fitting by the smallest covariance eigenvector follows the
closest-fit plane formulation introduced by Pearson [1]. The signed polygon area
and area-centroid formulas are standard planar polygon identities derivable from
Green's theorem; the implementation follows the conventional computational
geometry form summarized by O'Rourke [2].

The following are project-specific `mdstats` constructions:

- exact binding of natural-tiling windows to primitive-ring and framework-path
  identities;
- framework-relevant source compatibility that ignores spectator-only bonds;
- deterministic lifted T/O polygon reconstruction under the existing atomic and
  projected-framework periodic gauges;
- separation of ordered ring normal from the two inward side normals;
- immutable two-sided local frames tied to `TileSideRef` incidences;
- explicit unresolved records instead of guessed bridges or repaired polygons;
- deterministic source replay and canonical catalog digests.

No pore-center optimization, Voronoi construction, energetic site inference, or
trajectory smoothing algorithm is claimed.

# Public API

```python
build_reference_ring_geometry_catalog(
    tiling_geometry: TilingGeometryCatalog,
    complex_: PeriodicCellComplex,
    ring_index: PrimitiveRingIndex,
    topology: FrameworkTopology,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    *,
    frame_index: int = 0,
    options: RingGeometryOptions | None = None,
    resources: RingGeometryResources | None = None,
) -> ReferenceRingGeometryCatalog
```

The selected frame must use the unique-minimum-image atomic-connectivity
convention. Natural-tiling, cell-complex, primitive-ring, and framework graph
digests must agree transactionally before per-ring work begins.

# Source compatibility

## Framework-path binding

The complete source atomic-connectivity digest is recorded, but it is not the
default compatibility criterion. Framework projection intentionally ignores
spectator-only edges; cation--oxygen changes therefore must not invalidate the
chemical identity of a T--O--T ring.

The selected state is compatible when:

1. every framework vertex and linker required by the topology is present with
   the same atomic number;
2. every atomic edge in every projected framework path is present with the same
   canonical image shift; and
3. the atomic periodic gauge can be replayed under the unique-minimum-image
   convention.

The canonical set of replayed framework atomic edges is hashed as
`framework_path_binding_digest`.

`source_connectivity_exact_match` reports whether the selected complete state
also equals `FrameworkTopology.source_connectivity_digest`. Setting

```python
RingGeometryOptions(require_exact_source_connectivity=True)
```

changes this diagnostic into a strict requirement.

# Persistent ring identity

Every `ReferenceRingGeometry` is indexed by one `TopologicalWindow` and retains:

- dense `window_index` and source `face_index`;
- face and primitive-ring digests;
- primitive-ring ID and ring order;
- ordered lifted T atom/image references;
- ordered lifted O atom/image references;
- the two original `TileSideRef` incidences;
- explicit resolution status and message.

The ring order and orientation are inherited from the scientific face placement.
They are never rediscovered from atomistic coordinates.

# T and O polygon resolution

For every oriented primitive-ring edge, the bound `FrameworkEdgePath` must:

- have endpoints matching the oriented T walk;
- contain exactly one internal linker atom;
- contain exactly three atomic path vertices; and
- identify the internal linker with the configured oxygen atomic number.

Failure produces

```text
missing-or-ambiguous-oxygen-bridge
```

rather than choosing a nearby atom geometrically.

The lifted oxygen image is resolved by replaying the minimum-image T--O and O--T
segments in the selected atomic state. The reconstructed path must close onto
the lifted target T vertex within `path_closure_tolerance`.

# Geometric center and plane

For ordered O coordinates $\mathbf x_i$, the vertex centroid is

$$
\mathbf c_v=\frac{1}{k}\sum_{i=1}^{k}\mathbf x_i.
$$

Define the covariance matrix

$$
C=\frac{1}{k}\sum_i
(\mathbf x_i-\mathbf c_v)(\mathbf x_i-\mathbf c_v)^{\mathsf T}.
$$

The unit eigenvector associated with the smallest eigenvalue is the unsigned
least-squares normal. Its sign is fixed by the ordered vector area

$$
\mathbf A=\frac12\sum_i
(\mathbf x_i-\mathbf c_v)\times
(\mathbf x_{i+1}-\mathbf c_v),
$$

requiring $\hat{\mathbf n}\cdot\mathbf A>0$.

After projection into an orthonormal in-plane basis, let
$(u_i,v_i)$ denote polygon vertices and

$$
a_i=u_i v_{i+1}-u_{i+1}v_i.
$$

The signed area and centroid are

$$
A=\frac12\sum_i a_i,
$$

$$
\bar u=\frac{1}{6A}\sum_i(u_i+u_{i+1})a_i,
\qquad
\bar v=\frac{1}{6A}\sum_i(v_i+v_{i+1})a_i.
$$

The projected polygon must be simple: nonadjacent boundary segments may not
intersect or overlap. The area centroid must lie inside or on the boundary of the
simple projected polygon. Otherwise the record is explicitly unresolved rather
than exposing a misleading center aperture.

The three-dimensional projected-area centroid is the authoritative
`geometric_center` for Stage 11C1. The O vertex centroid is retained separately.

# Two-sided local frames

Every natural-tiling window owns two incidences. For side $s$, the inward normal
is obtained by combining the ordered ring normal with the incidence orientation.
The two normals must be exactly opposite within numerical tolerance.

Each `RingSideFrame` stores

$$
\mathcal F_{R,s}=
(\mathbf c_{\mathrm O,A},\hat{\mathbf n}_{R,s},
\hat{\mathbf e}_{1,s},\hat{\mathbf e}_{2,s}),
$$

with an orthonormal right-handed basis:

$$
\hat{\mathbf e}_{1,s}\times\hat{\mathbf e}_{2,s}
=
\hat{\mathbf n}_{R,s}.
$$

These are persistent topological side frames, not physical site nodes.

# Descriptors

Resolved records retain:

- covariance eigenvalues;
- ordered vector-area magnitude;
- projected polygon area;
- perimeter;
- RMS and maximum plane deviation;
- puckering amplitude;
- in-plane covariance ellipticity;
- center-to-boundary aperture witness;
- T--O and O--T bond-length sequences.

The aperture is the minimum in-plane distance from the projected-area centroid to
polygon boundary segments. It is a center-based descriptor, not a certified
maximum free-sphere radius.

# Explicit unresolved states

The first release defines:

```text
resolved
missing-or-ambiguous-oxygen-bridge
degenerate-oxygen-polygon
source-path-mismatch
```

Unresolved records retain persistent ring/window identity and a message, but do
not carry partial polygon geometry. This prevents downstream code from treating
an incomplete center or normal as scientific data.

# Resource policy

`RingGeometryResources` preflights:

- maximum number of windows;
- maximum ring order; and
- maximum bridge-distance and projected-segment intersection tests.

All limits are checked before catalog construction begins. Resource failure
produces no partial scientific artifact.

# Serialization and immutability

The catalog uses canonical JSON ordering and a SHA-256 digest. `from_dict()`
rebuilds the catalog from the supplied scientific sources and requires exact
payload equality. Tampered descriptors, source identities, statuses, or options
are rejected.

All records are frozen and contain immutable tuples. The selected atomistic frame
is independently fingerprinted from atomic numbers, periodic flags, cell,
origin, fractional positions, and frame ID.

# Validation requirements

Focused validation must include:

- all 58 LTA windows resolved with ring counts $36:16:6$ for 4R:6R:8R;
- exactly one oxygen per T--T edge;
- finite positive areas, perimeters, and bond lengths;
- opposite, orthonormal, right-handed side frames;
- distinction between T-face, O-vertex, and O-area centers;
- invariance under per-atom integer wrapping;
- correct translation and isotropic-scaling behavior;
- explicit unresolved output for a wrong bridge species;
- strict complete-source mode;
- transactional resource rejection;
- deterministic replay and tamper rejection;
- regression of Stage 11A and certified LTA natural tiling.

# Deferred boundary

Stage 11C1 does not implement:

- compatible-frame ring time series;
- normal continuity or dynamic sign tracking;
- LTA D4R/$\alpha$/$\beta$ semantics;
- species-dependent centered, side-offset, off-center, or annular sites;
- ion assignment, residence intervals, transition events, or rates.

Those belong to Stages 11C2, 11D, and 11E.

# References

[1] Pearson, K. (1901). *On Lines and Planes of Closest Fit to Systems of
Points in Space*. Philosophical Magazine, Series 6, 2(11), 559--572. DOI:
[10.1080/14786440109462720](https://doi.org/10.1080/14786440109462720).

[2] O'Rourke, J. (1998). *Computational Geometry in C*, 2nd edition. Cambridge
University Press.
