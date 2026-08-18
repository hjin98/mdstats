---
title: "Embedded Face Placement Specification"
subtitle: "Stage 8C: Exact Bounded PL Disks, Linking Certificates, and Witness Constraints"
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

Stage 8C introduces source-bound scientific face candidates on the exact periodic
straight-edge embedding established by Stages 8A--8B. Runtime/API target:

```text
mdstats 0.19.22a0
```

The stage answers three separate questions:

1. Does a primitive-ring placement admit an embedded piecewise-linear disk in a
   declared finite witness family?
2. Does a particular disk avoid forbidden framework penetration?
3. What rigorous linking or compatibility statement follows for a pair of
   particular witnesses?

The implementation deliberately separates these questions. A geometrically
embedded disk can be penetrated by another framework edge. Such a disk is not an
admissible face witness, but it remains a valid spanning surface for an algebraic
ring--surface linking certificate.

Stage 8C does **not** select the natural tiling, construct a cell complex, prove a
periodic partition, recognize arbitrary knots or links, or search unbounded
Steiner-surface families. Those responsibilities remain downstream.

# Source contract

The public builders require mutually consistent instances of:

```text
PeriodicNetView
PeriodicNetEmbedding
PrimitiveRingIndex
PeriodicEdgeIntersectionCertificate
RingPlacement
```

The first backend requires

```text
ProjectedEdgeCurveModel.STRAIGHT_SEGMENT
```

and rejects mixed source digests. Face construction is permitted only when the
Stage-8B global edge certificate is intersection-free. Otherwise the result is
`INVALID_REFERENCE_EMBEDDING`; no triangulation search is attempted.

All scientific geometry is evaluated in exact rational fractional coordinates.
Because the lattice map is invertible, incidence and orientation signs are affine
invariants; no floating Cartesian tolerance enters a certificate.

# Scientific identity versus auxiliary witness

A face is identified by its oriented ring placement, not by a triangulation:

```python
FacePlacement(
    periodic_net_embedding_digest: str,
    primitive_ring_catalog_digest: str,
    ring_placement: RingPlacement,
    orientation: Literal[-1, 1],
)
```

`orientation` selects one of the two cyclic boundary orientations. The canonical
SHA-256 digest includes the exact source embedding, primitive-ring catalog, ring
key, lattice image, and orientation.

A particular finite geometric realization is separate:

```python
FaceEmbeddingWitness(
    face_placement: FacePlacement,
    witness_id: int,
    method: FaceWitnessMethod,
    triangles: tuple[tuple[int, int, int], ...],
    periodic_self_candidate_set_digest: str,
    framework_candidate_set_digest: str,
    framework_contacts: tuple[FaceFrameworkContact, ...],
)
```

Multiple witnesses may certify one `FacePlacement`. Their triangle indices are
auxiliary proof data and do not create duplicate scientific faces.

# Finite disk family

The first method is

```text
BOUNDARY_VERTEX_TRIANGULATION
```

For a cyclic boundary with $n\ge 3$ vertices, it enumerates every combinatorial
triangulation using only those boundary vertices. The family has Catalan size

$$
N_{\mathrm{tri}}(n)=C_{n-2}
=\frac{1}{n-1}\binom{2n-4}{n-2}.
$$

Every candidate contains exactly $n-2$ oriented triangles. Boundary edges occur
once with the declared cyclic orientation; every internal diagonal occurs twice
with opposite orientations.

This is a complete exhaustion of the declared finite family, not a complete
spanning-disk theorem. Hass, Snoeyink, and Thurston show that embedded PL spanning
disks may require substantially more complexity than is visible in the boundary
polygon [3]. Therefore:

- exhaustion with no embedded candidate yields
  `UNRESOLVED_NO_EMBEDDED_WITNESS`;
- exhaustion with only penetrated embedded candidates yields
  `UNRESOLVED_NO_ADMISSIBLE_WITNESS`;
- neither status implies that the boundary is knotted or cannot bound some other
  disk.

# Exact geometric predicates

The private `_robust_geometry.py` kernel converts all coordinates to
`fractions.Fraction` and uses exact signs for:

- triangle nondegeneracy;
- segment--triangle intersection;
- triangle--triangle intersection;
- coplanar clipping;
- point-on-segment decisions;
- oriented transverse crossing signs.

The design follows Shewchuk's principle that combinatorial geometric decisions must
be determined by reliable signs rather than an arbitrary floating tolerance [1].
The noncoplanar triangle-intersection decomposition is related to the classical
Moller interval construction [2], while all degeneracies are handled by exact
rational predicates in this implementation.

An exact intersection record has topological dimension

```text
EMPTY, POINT, SEGMENT, or AREA
```

and preserves exact points, segment parameters, coplanarity, strict triangle
interior membership, and transverse orientation sign where defined.

# Embedded-disk certification

For each finite triangulation, Stage 8C performs:

1. exact rejection of degenerate triangles;
2. periodic triangle AABB broad-phase construction;
3. exact triangle--triangle tests for every surviving image-labelled candidate;
4. allowance only for the simplicial contacts prescribed by the mesh itself; and
5. rejection of all other same-image or periodic-image self-intersections.

A same-image contact is allowed only when it is confined to the common simplicial
vertex or common simplicial edge of the two triangles. Contacts with a nonzero
relative image are never interpreted as internal mesh adjacency.

Rejections are explicit:

```text
DEGENERATE_TRIANGLE
SURFACE_SELF_INTERSECTION
PERIODIC_SELF_INTERSECTION
```

The periodic image domain is supplied by `_periodic_spatial.py`; it is derived
from the actual continuous support bounds and is never a fixed
$[-1,1]^3$ shell.

# Framework penetration

Every embedded witness is tested against every periodic projected-edge image that
survives the broad phase. Contacts belonging to the face boundary itself are
allowed. Other contacts are recorded as:

```text
TRANSVERSE_INTERIOR
ENDPOINT_ON_INTERIOR
NONBOUNDARY_CONTACT
COPLANAR_OVERLAP
```

A witness is admissible exactly when

```python
witness.admissible == (not witness.framework_contacts)
```

Framework penetration is not folded into surface self-intersection. This preserves
the distinction

$$
\text{embedded spanning disk}
\quad\neq\quad
\text{admissible framework face}.
$$

# Face certificate

```python
FacePlacementCertificate(
    periodic_net_view_digest: str,
    topology_graph_digest: str,
    periodic_net_embedding_digest: str,
    primitive_ring_catalog_digest: str,
    periodic_edge_intersection_certificate_digest: str,
    face_placement: FacePlacement,
    triangulation_candidate_count: int,
    witnesses: tuple[FaceEmbeddingWitness, ...],
    rejections: tuple[FaceWitnessRejection, ...],
    status: FacePlacementStatus,
)
```

The witness and rejection counts exhaust the finite triangulation family unless
the Stage-8B reference embedding was invalid. Status semantics are:

| Status | Meaning |
|---|---|
| `CERTIFIED_ADMISSIBLE` | At least one exact embedded disk has no forbidden framework contact. |
| `UNRESOLVED_NO_ADMISSIBLE_WITNESS` | Embedded disks exist, but every searched witness is framework-penetrated. |
| `UNRESOLVED_NO_EMBEDDED_WITNESS` | No disk in the declared finite family passed embeddedness. |
| `INVALID_REFERENCE_EMBEDDING` | The required straight-edge reference embedding was not globally certified. |

`from_dict(...)` deterministically rebuilds the certificate from the supplied
sources and rejects any payload that is not byte-for-byte canonical after JSON
normalization.

# Algebraic linking certificate

Let $C_1$ be an oriented ring and $S_2$ an oriented spanning surface with
$\partial S_2=C_2$. Under the disjoint-boundary hypotheses,

$$
I(C_1,S_2)=\operatorname{lk}(C_1,C_2).
$$

Stage 8C computes $I$ by summing exact transverse segment--triangle signs within
each explicit relative lattice image. Shared boundary contacts are excluded only
when the exact contact is geometrically confined to the actual shared lifted
vertex or edge. Nonshared tangencies, endpoint contacts, and coplanar contacts are
counted as unresolved degeneracies rather than assigned an orientation sign.

For one image shift $\mathbf n$, the stored record is

```python
FaceAlgebraicIntersection(
    relative_image_shift: LatticeShift,
    intersection_number: int,
    transverse_crossing_count: int,
    unresolved_contact_count: int,
)
```

Any nonzero `intersection_number` is a rigorous linking certificate. A zero value
is not an unlinking theorem because signed crossings can cancel. The simplicial
intersection viewpoint follows Hsieh, Kauffman, and Tsau [4].

# Particular-witness compatibility

Two particular triangulated disks are also intersected exactly. This has a
different scientific meaning from linking of their boundaries:

- a forbidden disk--disk contact proves only that these witness choices are
  incompatible;
- disjoint embedded disks are an explicit unlinking witness for the supported
  two-component disk-bounding case;
- prescribed common lifted boundary vertices or edges are compatible;
- a nontransverse ring--surface degeneracy remains unresolved.

The ordered decision is:

| Pair status | Certificate meaning |
|---|---|
| `PROVEN_LINKED_NONZERO_INTERSECTION` | At least one image has nonzero algebraic ring--surface intersection. |
| `WITNESS_PAIR_INCOMPATIBLE` | No nonzero linking certificate, but the two particular surfaces meet outside prescribed shared boundary. |
| `UNRESOLVED_LINKING` | No nonzero sum, but a nonshared ring--surface contact lacks a transverse sign. |
| `COMPATIBLE_SHARED_BOUNDARY` | Surface contacts are confined to prescribed common boundary features. |
| `DISJOINT_DISK_WITNESS` | The two searched disks are disjoint and all linking sums are zero. |

The pair certificate is source-replay verified during deserialization.

# Finite compatibility constraint system

The compatibility layer treats a witness choice as a finite-domain assignment:

```python
FaceWitnessAssignment(
    face_placement_digest: str,
    witness_id: int,
    witness_digest: str,
)
```

`build_face_compatibility_constraint_system(...)` emits:

- unary forbidden assignments for framework-penetrated witnesses;
- pair forbidden assignments for proven links or incompatible disks;
- unresolved pair constraints for degenerate linking cases;
- caller-declared forbidden tuples of arity three or greater;
- scientific face symmetry relations; and
- witness-equivariance relations when exact net and ring symmetry are supplied.

A simple pairwise graph is insufficient because downstream face realizability can
require higher-order restrictions. The constraint system therefore stores explicit
tuples and never silently reduces them to pair constraints.

Symmetry acts first on the scientific `FacePlacement`. A mapped triangulation is
used only to relate equivalent witnesses when the exact image occurs in the target
certificate. Scientific face identity does not require invariant triangulation IDs.

# Public API

```python
make_face_placement(
    embedding,
    ring_index,
    ring_placement,
    *,
    orientation=1,
) -> FacePlacement

build_face_placement_certificate(
    view,
    embedding,
    ring_index,
    edge_certificate,
    face_placement,
    *,
    method=PeriodicSpatialMethod.AUTO,
    spatial_resources=None,
    resources=None,
) -> FacePlacementCertificate

certify_face_witness_pair(
    embedding,
    ring_index,
    left_witness,
    right_witness,
    *,
    method=PeriodicSpatialMethod.AUTO,
    spatial_resources=None,
    resources=None,
) -> FaceWitnessPairCertificate

map_face_placement(
    face,
    symmetry,
    ring_symmetry,
    operation_index,
) -> FacePlacement

build_face_compatibility_constraint_system(
    embedding,
    ring_index,
    certificates,
    *,
    method=PeriodicSpatialMethod.AUTO,
    spatial_resources=None,
    resources=None,
    higher_order_forbidden=(),
    symmetry=None,
    ring_symmetry=None,
) -> FaceCompatibilityConstraintSystem
```

# Resource and failure policy

```python
FaceEmbeddingResources(
    max_boundary_vertices=32,
    max_triangulations=100_000,
    max_exact_triangle_tests=5_000_000,
    max_framework_contact_tests=5_000_000,
    max_pair_witness_combinations=100_000,
)
```

Limits are checked transactionally. Resource exhaustion raises
`FaceCandidateResourceError`; it never returns a partial certificate that could be
mistaken for exhaustive mathematics. `_periodic_spatial.py` retains its own
independent object, translation-image, candidate, grid, and insertion guards.

# Determinism and persistence

All identity-bearing records are immutable. Canonical ordering is used for:

- triangulations and oriented triangle rotations;
- exact contact records;
- witnesses and pair certificates;
- assignments and constraints;
- symmetry relations;
- JSON keys and SHA-256 digests.

The public persistent schemas are:

```text
mdstats.face-placement.v1
mdstats.face-embedding-witness.v1
mdstats.face-placement-certificate.v1
mdstats.face-witness-pair-certificate.v1
mdstats.face-compatibility-constraints.v1
```

Broad-phase candidate sets remain transient derived workspaces. Persistent records
store their digests so geometric proof provenance is retained without embedding the
potentially large candidate lists.

# Focused validation

Stage-8C focused tests cover:

- two distinct triangulations certifying one planar scientific square face;
- a nonplanar quadrilateral with an embedded disk;
- embedded but framework-penetrated witnesses;
- a Hopf-link fixture with nonzero algebraic intersection;
- intersecting particular disks with zero linking sum;
- disjoint disk unlinking witnesses;
- prescribed shared-boundary compatibility;
- higher-order forbidden witness tuples;
- transactional Catalan-family resource failure;
- exact near-degenerate segment--triangle signs; and
- deterministic face and pair certificate replay with tamper rejection.

# Limitations and downstream contract

The following remain unresolved or deferred by design:

1. disks requiring interior Steiner vertices or more general PL surfaces;
2. complete knot or link recognition when the linking number vanishes;
3. non-straight projected framework edges;
4. automatic discovery of higher-order incompatibilities beyond supplied tuples;
5. a global face-selection solver;
6. translation-labelled chain groups and boundary operators;
7. tile-shell closure, volume overlap, and periodic partition certification.

Stage 9 must consume scientific `FacePlacement` objects plus a mutually compatible
witness assignment. It must not promote triangulation IDs into persistent face
identity.

# References

[1] J. R. Shewchuk, "Adaptive Precision Floating-Point Arithmetic and Fast Robust
Geometric Predicates," *Discrete & Computational Geometry* **18**, 305--363
(1997). DOI: 10.1007/PL00009321.

[2] T. Moller, "A Fast Triangle-Triangle Intersection Test," *Journal of Graphics
Tools* **2**(2), 25--30 (1997). DOI: 10.1080/10867651.1997.10487472.

[3] J. Hass, J. Snoeyink, and W. P. Thurston, "The Size of Spanning Disks for
Polygonal Curves," *Discrete & Computational Geometry* **29**, 1--17 (2003).
DOI: 10.1007/s00454-002-2707-6.

[4] C.-C. Hsieh, L. H. Kauffman, and C.-M. Tsau, "A Combinatorial Algorithm for
Computing Higher Order Linking Numbers," *Asian Journal of Mathematics* **21**,
265--286 (2017). DOI: 10.4310/AJM.2017.v21.n2.a3.
