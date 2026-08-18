---
title: "Periodic Extended-Object Broad Phase and Edge-Intersection Specification"
subtitle: "Stage 8B: Image-Labelled Candidate Generation and Exact Straight-Edge Certification"
author: "mdstats"
date: "2026-07-18"
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

# Purpose and boundary

Stage 8B adds two distinct layers:

1. `_periodic_spatial.py`, a private query-agnostic broad phase for bounded
   continuous lifted supports; and
2. `periodic_edge_intersection.py`, a public exact certificate for the global
   periodic straight-edge embedding produced by Stage 8A.

Runtime/API target:

```text
mdstats 0.19.21a0
```

The broad phase answers only:

> Which explicit periodic image placements of bounded supports cannot be ruled
> out by conservative support overlap?

It does not decide intersection, distance, linking, penetration, face validity,
properness, or tile overlap. Those meanings belong to downstream exact
consumers.

The edge certificate answers:

> Does any pair of projected straight-edge instances intersect anywhere in the
> infinite periodic lift, except at a shared lifted graph vertex?

The result is a verification certificate, not a replacement for
`PeriodicNetEmbedding`, `PeriodicNetView`, or `FrameworkTopology`.

# Ownership model

```text
PeriodicNetEmbedding
    -> continuous lifted edge supports
       -> _periodic_spatial candidate set
          -> exact rational segment predicates
             -> PeriodicEdgeIntersectionCertificate
```

The private candidate set is derived workspace. The persistent scientific record
contains source digests, diagnostics, and forbidden exact contacts only.

# Algorithmic provenance

The linked-cell decomposition is adapted from the classical neighbor-search
method of Quentrec and Brot [1]. The extension to continuous lifted objects,
explicit relative image labels, multi-bin occupancy, deterministic candidate
canonicalization, automatic grid selection, and query-independent support records
is an `mdstats` design.

The exact segment predicate uses standard rational vector algebra. No floating
orientation tolerance is used. The observation that intersection may be tested
in fractional coordinates follows directly from affine invariance under the
invertible lattice map.

# Continuous lifted support

Every bounded object is represented by one connected, unwrapped realization in
fractional coordinates. For an object $A$, its conservative support is the closed
axis-aligned box

$$
B_A=[\boldsymbol\ell_A,\mathbf u_A]\subset\mathbb R^3.
$$

Coordinates may lie outside $[0,1)^3$. Wrapping a boundary-crossing object before
building its support is forbidden because it can produce an artificially large or
disconnected support.

The v1 support record is:

```python
PeriodicAabbSupport(
    object_id: int,
    lower: tuple[Fraction, Fraction, Fraction],
    upper: tuple[Fraction, Fraction, Fraction],
)
```

`object_id` is a dense deterministic position in the consumer's source sequence.
The helper `from_points()` builds the exact closed AABB and may apply a
nonnegative per-axis inflation. Inflated supports allow the same broad phase to
serve finite-range distance or buffered predicates.

# Periodic image candidates

For two supports $A$ and $B$, the image of $B$ translated by
$\mathbf n\in\mathbb Z^3$ is

$$
B_{\mathbf n}=B+\mathbf n.
$$

A candidate survives when the closed fractional AABBs overlap on every axis:

$$
\ell_{A,k}\le u_{B,k}+n_k,
\qquad
\ell_{B,k}+n_k\le u_{A,k},
\qquad k=1,2,3.
$$

This rule is conservative for every exact predicate whose satisfaction requires a
common point in the two supports.

Candidate identity is

```python
PeriodicImageCandidate(
    object_i: int,
    object_j: int,
    image_shift: LatticeShift,
)
```

with the equivalence

$$
(i,j,\mathbf n)\sim(j,i,-\mathbf n).
$$

The stored representative satisfies $i\le j$. For a self-image candidate
$i=j$, the zero image is excluded and one deterministic sign representative of
$\mathbf n$ and $-\mathbf n$ is retained. Nonzero self-image candidates remain
valid and must not be collapsed.

# Complete translation stencil

Let

$$
\ell_k^{\min}=\min_A \ell_{A,k},
\qquad
u_k^{\max}=\max_A u_{A,k}.
$$

Any overlapping image pair must satisfy

$$
\left\lceil\ell_k^{\min}-u_k^{\max}\right\rceil
\le n_k\le
\left\lfloor u_k^{\max}-\ell_k^{\min}\right\rfloor.
$$

The Cartesian product of these three integer ranges is a complete finite global
stencil. It is not a fixed $[-1,1]^3$ assumption; larger lifted supports
produce larger proved ranges. Construction fails transactionally when the
stencil exceeds the declared image resource.

# Direct broad phase

The direct backend tests every canonical object pair against every stencil image,
excluding the zero-image self pair. Exact fractional AABB overlap is then applied.

Its nominal work is

$$
O\!\left(N^2|\mathcal S|\right),
$$

where $N$ is the object count and $|\mathcal S|$ is the complete stencil size.
It is preferred automatically for small problems because it has low overhead and
is an exhaustive oracle for linked-cell validation.

# Extended-object linked cells

The linked-cell backend uses a uniform fractional grid with $k$ subdivisions per
lattice coordinate. It operates in continuous lifted space rather than wrapping
objects into one cell.

For each grid candidate:

1. every canonical support $A$ is inserted into every integer bin touched by its
   closed AABB;
2. every explicit image placement $B+\mathbf n$ for
   $\mathbf n\in\mathcal S$ is inserted into every touched bin;
3. canonical/image records sharing a bin generate a provisional candidate;
4. provisional candidates are canonicalized and deduplicated; and
5. exact fractional AABB overlap removes false positives.

Closed upper bounds are inserted into the bin containing the boundary. This may
increase false positives at bin planes but prevents missed endpoint contacts.

The automatic grid selector evaluates deterministic powers of two

$$
k\in\{1,2,4,\ldots,k_{\max}\}
$$

and minimizes

$$
C(k)=N_{\rm insert}(k)+N_{\rm bin\ pair}(k)
$$

subject to resource limits. Correctness is independent of the selected grid.

# Broad-phase API

```python
class PeriodicSpatialMethod(str, Enum):
    AUTO = "auto"
    DIRECT = "direct"
    LINKED_CELL = "linked-cell"

class PeriodicSpatialResources:
    max_objects: int
    max_translation_images: int
    max_image_placements: int
    max_candidate_checks: int
    max_candidates: int
    max_bin_insertions: int
    max_grid_subdivisions: int
    direct_candidate_check_limit: int

build_periodic_overlap_candidates(
    supports,
    *,
    source_digest,
    method=PeriodicSpatialMethod.AUTO,
    resources=None,
) -> PeriodicSpatialCandidateSet
```

`PeriodicSpatialCandidateSet` records the selected method, complete stencil,
canonical candidates, selected grid, placement/insertion/check counts, and a
canonical digest. It is private derived workspace and is not exported from the
package analysis namespace.

# Exact periodic straight-edge predicate

For two segment placements

$$
P(t)=\mathbf p+t\mathbf r,
\qquad
Q(u)=\mathbf q+u\mathbf s,
\qquad 0\le t,u\le1,
$$

all coordinates are exact `Fraction` values.

## Nonparallel segments

Let

$$
\mathbf c=\mathbf r\times\mathbf s.
$$

If $\mathbf c\ne0$, the supporting lines can intersect only when

$$
(\mathbf q-\mathbf p)\cdot\mathbf c=0.
$$

The exact parameters are

$$
t=\frac{[(\mathbf q-\mathbf p)\times\mathbf s]\cdot\mathbf c}
        {\mathbf c\cdot\mathbf c},
\qquad
u=\frac{[(\mathbf q-\mathbf p)\times\mathbf r]\cdot\mathbf c}
        {\mathbf c\cdot\mathbf c}.
$$

An intersection exists exactly when both parameters lie in $[0,1]$.

## Parallel and collinear segments

If $\mathbf r\times\mathbf s=0$, collinearity requires

$$
(\mathbf q-\mathbf p)\times\mathbf r=0.
$$

The segments are projected onto any coordinate where $r_k\ne0$. Exact interval
overlap distinguishes:

- no contact;
- one-point contact; and
- positive-length collinear overlap.

Zero-length edges are already rejected by `PeriodicNetEmbedding` and remain an
input error for the predicate.

# Affine invariance

The authoritative Cartesian coordinate is

$$
\mathbf r=\mathbf fH,
$$

where $H$ is invertible. An invertible affine map preserves segment incidence,
endpoint/interior status, and collinearity. Therefore exact intersection may be
decided in rational fractional coordinates without introducing floating-point
roundoff from the Cholesky cell.

# Scientific contact semantics

For the left edge at anchor image $\mathbf0$ and the right edge at relative image
$\mathbf n$, endpoint identities are exact lifted vertices:

$$
(i,\mathbf a),
\qquad
(j,\mathbf a+\boldsymbol\delta_e).
$$

Contacts are classified as:

```text
ALLOWED_COMMON_VERTEX
FORBIDDEN_PROPER_CROSSING
FORBIDDEN_ENDPOINT_ON_INTERIOR
FORBIDDEN_DISTINCT_ENDPOINT_CONTACT
FORBIDDEN_COLLINEAR_OVERLAP
```

A point contact is allowed only when both segment parameters are endpoints and the
two endpoint records are the same `LiftedVertexRef`. Geometric coincidence alone
is insufficient.

The following invalidate the straight-edge embedding:

- two nonincident interiors crossing;
- one edge endpoint lying in another edge interior;
- endpoints of distinct lifted vertices occupying the same point; and
- any positive-length collinear overlap, including overlap between self-images.

# Public certificate API

```python
certify_periodic_straight_edge_embedding(
    view: PeriodicNetView,
    embedding: PeriodicNetEmbedding,
    *,
    method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
    resources: PeriodicSpatialResources | None = None,
) -> PeriodicEdgeIntersectionCertificate
```

Result status:

```python
class PeriodicEdgeIntersectionStatus(str, Enum):
    CERTIFIED_INTERSECTION_FREE = "certified-intersection-free"
    FORBIDDEN_INTERSECTIONS_FOUND = "forbidden-intersections-found"
```

The certificate stores:

- exact view, topology, embedding, and broad-phase candidate-set digests;
- selected broad-phase method;
- edge, image, candidate, and exact-test counts;
- the number of allowed common-vertex contacts; and
- every forbidden exact contact.

Allowed contacts are counted but not persisted individually. They are derivable
workspace rather than scientific failures.

# Serialization and verification

Schema:

```text
mdstats.periodic-edge-intersection-certificate.v1
```

Deserialization requires the exact `PeriodicNetView` and
`PeriodicNetEmbedding`. The complete broad phase and exact predicate are replayed,
and the reconstructed canonical payload must equal the stored payload. A modified
JSON object with a recomputed digest therefore cannot certify a false embedding.

# Input constraints

The first certificate requires:

- one exact `PeriodicNetView`;
- one source-compatible `PeriodicNetEmbedding`;
- `ProjectedEdgeCurveModel.STRAIGHT_SEGMENT`;
- identical ordered vertex and edge identities in the view and embedding;
- nonzero embedded edges; and
- sufficient declared broad-phase resources.

The method supports multiedges and nonzero projected self-edges. Distinct graph
edges are never merged by geometry.

# Resource failure semantics

Resource limits are transactional. Exceeding any of the following raises
`PeriodicSpatialResourceError` before returning a partial candidate set:

- support count;
- complete translation-stencil size;
- explicit image placements;
- direct/bin pair checks;
- final candidates; or
- linked-cell insertions.

The public exact certificate is therefore either complete for the declared
embedding or absent. There is no partial-success certification state.

# Edge cases

## Boundary-only overlap

Closed AABBs intentionally admit supports touching at one point or plane. The
exact predicate decides whether the contact is an allowed common vertex or a
forbidden geometric event.

## Skewed cells

No orthogonality is assumed. Fractional AABB overlap remains conservative because
an exact intersection point has equal fractional coordinates before and after the
invertible Cartesian cell map. False positives may increase for highly skewed
cells, but false negatives are not introduced.

## Supports spanning several cells

The stencil is derived from the actual lifted bounds. Supports may extend over
multiple lattice cells; fixed neighbor shells are not used as correctness
assumptions.

## Self images

$(i,i,\mathbf n)$ with $\mathbf n\ne0$ is preserved. This is required to detect
periodic self-crossing or overlap of one quotient object with another image of
itself.

## One-member and two-member graph rings

Such graph objects can remain topologically valid. If their straight-edge images
coincide or overlap, the Stage-8B certificate fails and a later distinct-curve
embedding model is required before they can serve as nondegenerate face geometry.

# Focused validation requirements

The Stage-8B gate must test:

1. direct and linked-cell candidate equality against exhaustive image enumeration;
2. explicit nonzero self-image retention and sign canonicalization;
3. support inflation for finite-range candidate rules;
4. transactional stencil/resource failure;
5. allowed shared lifted-vertex contacts;
6. exact nonincident proper crossings;
7. crossings appearing only in a nonzero periodic image;
8. collinear overlap versus point contact;
9. source-validated certificate replay; and
10. complete Na-LTA global straight-edge certification.

# Deferred work

Stage 8B does not yet implement:

- deformation-aware candidate-cache reuse;
- segment--triangle or triangle--triangle exact predicates;
- spanning-disk, linking, penetration, or tile-volume semantics;
- physical trajectory-frame mappings; or
- face selection and natural-tiling orchestration.

The generic broad phase is designed to support those consumers without changing
candidate identity.

# References

1. Quentrec, B., and Brot, C. (1973). *New Method for Searching for Neighbors
   in Molecular Dynamics Computations*. Journal of Computational Physics,
   13(3), 430-432. DOI:
   [10.1016/0021-9991(73)90046-6](https://doi.org/10.1016/0021-9991(73)90046-6).
