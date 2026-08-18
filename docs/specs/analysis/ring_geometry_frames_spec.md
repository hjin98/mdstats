---
title: "Compatible-Frame Oxygen-Ring Geometry Specification"
subtitle: "Stage 11C2: Fixed-Identity Ring Dynamics, Reference-Aligned Frames, and Explicit Unresolved States"
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

Stage 11C2 maps the immutable Stage-11C1 ring identities onto the same compatible
frames already certified by Stage 11B:

```text
reference ring catalog + compatible-frame tiling catalog
        + atomistic frame collection + atomic connectivity
        -> replay fixed T atom/image identities
        -> replay fixed O bridge identities and T-O-T closure
        -> instantaneous O-ring center, plane, and descriptors
        -> reference-aligned two-sided local frames
        -> explicit per-ring and per-frame resolution states
```

Runtime/API target:

```text
mdstats 0.19.88a0
```

Primary module:

```text
mdstats/analysis/ring_geometry_frames.py
```

Stage 11C2 is descriptive geometry. It does not assign ions, infer metastable
states, label LTA cage semantics, smooth trajectories, repair topology, or fit
rates.

# Source hierarchy

The Stage-11C1 `ReferenceRingGeometryCatalog` remains the authoritative source
of persistent window, primitive-ring, T-atom, O-atom, and side identities.
`FrameTilingGeometryCatalog` remains the authoritative source of frame
compatibility and the periodic projected-framework gauge. Stage 11C2 must not
rediscover a different gauge.

The following digests must agree before mapping begins:

- the natural-tiling geometry digest;
- the periodic-cell-complex digest;
- the selected collection/frame binding used by Stage 11B;
- the atomic-connectivity binding used by Stage 11B; and
- the Stage-11C1 reference-frame fingerprint.

# Public API

```python
map_ring_geometry_to_frames(
    reference_geometry: ReferenceRingGeometryCatalog,
    frame_tiling_geometry: FrameTilingGeometryCatalog,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    *,
    options: FrameRingGeometryOptions | None = None,
    resources: FrameRingGeometryResources | None = None,
) -> FrameRingGeometryCatalog
```

The mapped frame set is exactly the ordered frame set stored by
`frame_tiling_geometry`. Frame selection is therefore performed once, upstream,
by Stage 11B.

# Fixed-identity polygon replay

For a mapped Stage-11B frame, let the canonical projected-framework coordinate
of T atom $i$ be

$$
\mathbf f_i^{\mathrm{can}}(t)
=
\mathbf f_i^{\mathrm{wrap}}(t)
+
\mathbf g_i(t)
+
\mathbf G(t),
$$

where $\mathbf g_i(t)$ and $\mathbf G(t)$ are the stored Stage-11B vertex and
global gauges. The lifted T coordinate for reference ring atom/image record
$(i,\mathbf n_i)$ is

$$
\mathbf f_i^R(t)=\mathbf f_i^{\mathrm{can}}(t)+\mathbf n_i.
$$

The O atom identity is never reselected. For each fixed T--O--T bridge, the
instantaneous minimum-image T-to-O shift is replayed from the lifted source T.
The O-to-target-T leg must close onto the already mapped lifted target T within
`path_closure_tolerance`. The current connectivity state must contain both fixed
T--O and O--T atom pairs. Otherwise the ring receives an explicit missing-bridge
or gauge-failure state. Under the current Stage-11B graph-digest contract, a
changed framework-linker identity normally makes the whole frame
`topology_mismatch` before per-ring replay begins. The `missing_bridge` state is
therefore a defensive distinction for compatible future upstream policies or
other source bindings that preserve the projected graph identity while a fixed
bridge pair is unavailable.

# Instantaneous geometry

The O polygon uses the same Pearson closest-fit plane and projected polygon
area-centroid definitions as Stage 11C1. Each resolved frame stores:

- lifted T and O fractional and Cartesian polygons;
- O-vertex and O-area centers;
- ordered unit normal;
- two inward side frames;
- covariance eigenvalues;
- vector-area magnitude and projected area;
- perimeter;
- RMS and maximum planarity deviations;
- puckering amplitude;
- ellipticity;
- center aperture radius; and
- both ordered T--O distance arrays.

The O-area centroid remains a geometric center, not an ionic-site center.

# Reference-aligned orientation

The ordered normal is sign-aligned to the Stage-11C1 ordered normal:

$$
\mathbf n(t)\cdot\mathbf n_0 \ge 0.
$$

The in-plane frame uses corresponding O atoms. First, the reference basis is
transported to the current plane by the minimum rotation that maps
$\mathbf n_0$ to $\mathbf n(t)$. Then a two-dimensional proper orthogonal
Procrustes fit determines the in-plane rotation that best aligns the reference
and instantaneous projected O polygons. This is a descriptive orientation
convention, not a dynamical smoothing filter. The orthogonal Procrustes method
follows Schönemann [3].

The result stores:

$$
\theta_{\mathrm{tilt}}(t)
=
\cos^{-1}\!\left(\mathbf n_0\cdot\mathbf n(t)\right),
$$

and the signed in-plane rotation relative to the transported reference basis.

# Translation and deformation descriptors

For each resolved ring, Stage 11C2 reports:

- Cartesian center translation $\mathbf c(t)-\mathbf c_0$;
- fractional center translation in the current cell gauge;
- normal-reference dot product;
- tilt angle;
- signed in-plane rotation; and
- instantaneous geometric descriptors listed above.

No affine-cell correction is silently applied to the Cartesian translation.
Consumers requiring strain-removed motion must derive it explicitly from stored
fractional centers and cells.

# Resolution states

`FrameRingGeometryStatus` distinguishes:

- `mapped`;
- `reference_unresolved`;
- `topology_mismatch` inherited from Stage 11B;
- `missing_bridge` for absent fixed T--O/O--T connectivity;
- `gauge_failure` for unreplayable integer-image closure;
- `degenerate_geometry` for an invalid instantaneous O polygon; and
- `upstream_frame_unresolved` for other unresolved Stage-11B frame states.

Persistent ring identity is retained in every record. Partial frames are
allowed: one ring can be unresolved while other rings remain mapped.

At frame level:

- `mapped` means all reference-resolved rings mapped;
- `partially_mapped` means at least one but not all reference-resolved rings
  mapped; and
- `unresolved` means no reference-resolved ring mapped.

# Resource policy

Resource preflight occurs before mapping and bounds:

- selected frame count;
- ring count;
- total T/O vertex instances; and
- minimum-image pair tests.

No partial catalog is returned after a resource rejection.

# Immutability, serialization, and metric series

All records are frozen and use immutable tuples. The catalog digest is canonical.
`from_dict()` rebuilds the catalog from scientific sources and rejects any
noncanonical or tampered payload.

`ring_metric(window_index, metric)` returns a read-only frame-aligned NumPy array
and inserts `NaN` for unresolved ring frames. Supported scalar metrics include
area, perimeter, aperture, planarity, puckering, ellipticity, tilt, and
in-plane rotation.

# Validation requirements

Focused validation must include:

- all 58 LTA rings mapped on an unchanged compatible frame;
- equality with Stage-11C1 geometry on the reference frame;
- integer atom-wrapping invariance;
- trajectory-anchor translation continuity;
- isotropic scaling of lengths and areas;
- rigid rotation of centers, normals, and side frames;
- stable reference-aligned orientation under small deformation;
- partial-frame retention under one-ring degenerate geometry;
- topology-mismatch precedence for changed framework-linker identity;
- inherited topology mismatch;
- explicit gauge and degenerate-geometry failures;
- frame and ring resource preflight;
- deterministic metric series;
- canonical replay and tamper rejection; and
- regression of Stages 11A, 11B, and 11C1.

# Deferred boundary

Stage 11C2 does not implement framework semantic labels, species-dependent site
states, ion assignment, residence statistics, transition networks, or rate
models. Those remain Stages 11D and 11E.

# References

[1] Pearson, K. (1901). *On Lines and Planes of Closest Fit to Systems of
Points in Space*. Philosophical Magazine, Series 6, 2(11), 559--572. DOI:
[10.1080/14786440109462720](https://doi.org/10.1080/14786440109462720).

[2] O'Rourke, J. (1998). *Computational Geometry in C*, 2nd edition. Cambridge
University Press.

[3] Schönemann, P. H. (1966). *A generalized solution of the orthogonal
Procrustes problem*. Psychometrika 31, 1--10. DOI:
[10.1007/BF02289451](https://doi.org/10.1007/BF02289451).
