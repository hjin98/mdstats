---
title: "Periodic Net Embedding Specification"
subtitle: "Stage 8A: Symmetry-Compatible Authoritative Euclidean Realization"
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

`periodic_net_embedding.py` constructs one authoritative Euclidean reference
realization of an exact `PeriodicNetView`. The first backend combines:

1. the exact rational `PeriodicBarycentricPlacement` certified by automatic
   symmetry discovery;
2. the complete `PeriodicNetSymmetry` discovered for that view; and
3. a deterministic, basis-covariant positive-definite lattice metric derived
   from the complete set of projected quotient-edge vectors.

Runtime/API target:

```text
mdstats 0.19.20a0
```

The result is distinct from:

- the abstract connectivity and signature policy in `PeriodicNetView`;
- the rational placement, which has no Euclidean metric;
- an instantaneous or relaxed molecular-dynamics frame; and
- future face, tile, cage, or periodic spatial-intersection certificates.

Stage 8A establishes coordinates and projected straight-edge geometry only. It
does not certify global absence of crossings between nonincident periodic edge
images. That finite periodic spatial problem belongs to Stage 8B.

# Motivation

Natural-tiling topology must be constructed on one fixed, reproducible reference
embedding. Using an arbitrary trajectory frame would make the inferred tiling
depend on thermal noise, relaxation history, strain, and cell orientation. Using
fractional barycentric coordinates without a metric is also insufficient because
length, planarity, intersection, linking, and volume are Euclidean questions.

The intended ownership chain is

```text
PeriodicNetView
    -> PeriodicNetSymmetryDiscovery
       -> PeriodicBarycentricPlacement
       -> PeriodicNetSymmetry
    -> PeriodicNetEmbedding
```

The embedding is therefore source-bound to the exact view, complete symmetry
certificate, and barycentric placement from which it was constructed.

# Algorithmic provenance

The periodic quotient/vector representation follows Chung, Hahn, and Klee [1].
The exact barycentric/equilibrium placement and complete affine symmetry
framework follow Delgado-Friedrichs [2] and Delgado-Friedrichs--O'Keeffe [3].

The edge-covariance metric below is an `mdstats` derivation. It is chosen because
it is:

- exact over $\mathbb Q$ before final Cartesian factorization;
- invariant under every validated net automorphism;
- covariant under a unimodular change of lattice basis; and
- determined by the full projected quotient-edge set rather than by an arbitrary
  seed Euclidean metric in the input basis.

# Mathematical input

Let the exact barycentric coordinate of quotient vertex $i$ be

$$
\mathbf x_i\in\mathbb Q^3.
$$

For one canonical quotient edge

$$
e=(i,j,\boldsymbol\delta_e),
$$

its lifted fractional displacement is

$$
\mathbf d_e=\mathbf x_j+\boldsymbol\delta_e-\mathbf x_i.
$$

Parallel edges remain distinct graph records and contribute with multiplicity.
A zero displacement is a degenerate projected edge and is rejected.

# Exact edge-covariance metric

Define the symmetric edge second-moment matrix

$$
C=\sum_{e\in E_{\rm view}}\mathbf d_e\mathbf d_e^{\mathsf T}.
$$

The first backend requires the projected edge vectors to span three dimensions,
so $C$ is positive definite. Define

$$
G_{\mathbb Q}=C^{-1}.
$$

## Symmetry invariance

For a periodic-net automorphism with lattice action

$$
A_g\in GL(3,\mathbb Z),
$$

explicit edge permutation and orientation imply

$$
\mathbf d_{g(e)}=\pm A_g\mathbf d_e.
$$

Because the operation permutes the complete edge set,

$$
A_g C A_g^{\mathsf T}=C.
$$

Taking inverses gives

$$
A_g^{\mathsf T}G_{\mathbb Q} A_g=G_{\mathbb Q}.
$$

The implementation verifies this identity exactly for every stored operation.

## Lattice-basis covariance

For a unimodular basis change $P\in GL(3,\mathbb Z)$ with new fractional
coordinates

$$
\mathbf x'=P^{-1}\mathbf x,
$$

edge vectors and covariance transform as

$$
C'=P^{-1}CP^{-\mathsf T}.
$$

Therefore

$$
G_{\mathbb Q}'=P^{\mathsf T}G_{\mathbb Q} P,
$$

which is the correct transformation law for a lattice Gram matrix. This avoids
making the Euclidean shape depend on an arbitrary source-cell indexing choice.

## Primitive integral normalization

Clear all denominators of $G_{\mathbb Q}$ and divide the resulting integer matrix
by the greatest common divisor of all entries. The stored exact metric is the
primitive positive-definite integral Gram matrix

$$
G\in\mathbb Z^{3\times3}.
$$

This fixes the remaining positive rational scale while preserving shape and
symmetry.

# Cartesian realization

The exact scientific representation is the pair

$$
(\{\mathbf x_i\},G).
$$

For numerical Cartesian geometry, use the unit-volume Gram matrix

$$
\bar G=\frac{G}{(\det G)^{1/3}},
\qquad \det\bar G=1.
$$

Let $H$ be the deterministic lower-triangular Cholesky factor

$$
\bar G=HH^{\mathsf T}.
$$

`mdstats` stores lattice vectors as rows of `cell_matrix = H`. For a row
fractional coordinate $\mathbf f^{\mathsf T}$,

$$
\mathbf r^{\mathsf T}=\mathbf f^{\mathsf T}H.
$$

The Cartesian scale is dimensionless and has unit cell volume. Later consumers
that need physical lengths must use a separately supplied physical cell or a
validated mapping from this reference realization.

# Exact affine equivariance

Every normalized periodic automorphism acts on lifted vertices by

$$
g(i,\mathbf n)=
\left(\pi_g(i),A_g\mathbf n+\boldsymbol\tau_i^g\right).
$$

Let $i_0$ be the barycentric/symmetry anchor and

$$
\mathbf b_g=\mathbf x_{\pi_g(i_0)}.
$$

Because the normalized anchor image shift is zero, exact coordinate equivariance
requires

$$
A_g\mathbf x_i+\mathbf b_g
=
\mathbf x_{\pi_g(i)}+\boldsymbol\tau_i^g
$$

for every quotient vertex and every operation. Construction fails if any exact
identity is violated.

Since the first edge model is a straight segment, exact endpoint equivariance
also proves equivariance of every projected edge curve.

# Public API

```python
class PeriodicNetEmbeddingMethod(str, Enum):
    BARYCENTRIC_EDGE_COVARIANCE = "barycentric-edge-covariance-v1"


class ProjectedEdgeCurveModel(str, Enum):
    STRAIGHT_SEGMENT = "straight-segment-v1"
```

```python
@dataclass(frozen=True, slots=True)
class PeriodicNetEmbeddingResources:
    max_vertices: int = 4096
    max_edges: int = 16384
    max_symmetry_operations: int = 2048
    max_metric_fraction_bits: int = 4096
```

```python
@dataclass(frozen=True, slots=True)
class PeriodicNetEmbedding:
    periodic_net_view_digest: str
    topology_graph_digest: str
    periodic_net_symmetry_digest: str
    barycentric_placement_digest: str
    symmetry_discovery_certificate_digest: str
    method: PeriodicNetEmbeddingMethod
    edge_curve_model: ProjectedEdgeCurveModel
    anchor_atom_index: int
    vertex_atom_indices: tuple[int, ...]
    edge_keys: tuple[FrameworkEdgeKey, ...]
    fractional_coordinates: tuple[RationalVector3, ...]
    primitive_gram_matrix: tuple[tuple[int, int, int], ...]
    metric_determinant: int
    minimum_edge_length_squared: Fraction
    maximum_edge_length_squared: Fraction
    canonical_schema_version: str
    digest_algorithm: str
    digest: str
```

Builder:

```python
build_periodic_net_embedding(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    *,
    resources: PeriodicNetEmbeddingResources | None = None,
) -> PeriodicNetEmbedding
```

The builder accepts a complete discovery record rather than an arbitrary subgroup
so the authoritative metric is verified against the complete automorphism group
for the supported backend.

# Convenience geometry

The result supplies:

```python
embedding.fractional_coordinate(atom_index, image_shift=(0, 0, 0), wrap=False)
embedding.unit_volume_gram_matrix()
embedding.cell_matrix()
embedding.cartesian_coordinate(atom_index, image_shift=(0, 0, 0), wrap=False)
embedding.edge_segment(edge_key, anchor_shift=(0, 0, 0))
```

`edge_segment()` returns a transient `EmbeddedStraightEdgeSegment` containing
exact lifted fractional endpoints, derived Cartesian endpoints, the exact
primitive-metric squared length, and source identities. It does not create a new
persistent edge catalog.

# Input constraints

The first backend requires:

1. full three-dimensional periodicity;
2. one quotient component;
3. translation rank three and subgroup index one;
4. one complete `PeriodicNetSymmetryDiscovery` belonging to the exact view;
5. a collision-free exact barycentric placement;
6. a three-dimensional span of projected edge vectors;
7. no zero-length projected edge; and
8. no pair of distinct quotient-edge records represented by the same straight
   segment modulo lattice translation and reversal.

The final condition makes the first straight-segment model explicit. A multigraph
with coincident projected parallel edges requires a future distinct-curve backend;
it is not silently collapsed.

# Scope of spatial validation

Stage 8A certifies:

- distinct quotient vertices modulo lattice translation;
- nonzero projected edge lengths;
- no duplicate/coincident straight projected-edge records;
- exact vertex and edge equivariance under the complete symmetry group; and
- positive-definite lattice metric.

It does **not** yet certify that arbitrary nonincident edge images do not cross.
That requires periodic image enumeration, continuous lifted supports, and exact
segment predicates from Stage 8B. The embedding digest remains the source identity
for that later spatial certificate.

# Serialization and provenance

Schema:

```text
mdstats.periodic-net-embedding.v1
```

The embedding stores the digests of the exact view, core symmetry, and barycentric
placement. It also stores a ring-independent discovery-certificate digest computed
from the discovery method, source frame, placement digest, complete symmetry
digest, frame/candidate counts, and generator indices. Optional primitive-ring
symmetry data do not affect embedding identity.

Rational values are serialized as `[numerator, denominator]`.
`from_dict(..., view=..., discovery=...)` rebuilds the complete embedding and
requires canonical payload equality. A matching SHA-256 digest alone is not
scientific verification.

# Complexity

For $|E|$ quotient edges and symmetry-group order $|G|$:

- covariance construction: $O(|E|)$ exact rational operations;
- exact metric inversion: constant-size $3\times3$ arithmetic;
- vertex equivariance verification: $O(|G||V|)$;
- metric and edge equivariance verification: $O(|G|+|G||E|)$;
- coincident-segment detection in the first implementation: $O(|E|^2)$ exact
  comparisons.

The quadratic coincidence check is acceptable for the current moderate quotient
nets and will later be replaceable by the Stage-8B periodic spatial index.

# Failure policy

Construction is transactional. It raises a typed exception and returns no partial
embedding for:

- source digest mismatch;
- incomplete or incompatible discovery data;
- collided barycentric vertices;
- singular edge covariance;
- rational coefficient growth beyond the declared resource bound;
- failed exact metric or coordinate equivariance;
- zero-length projected edges;
- coincident distinct straight projected edges; or
- malformed serialization.

# Focused tests

The Stage-8A gate must verify:

- exact diamond-net metric and unit-volume Cartesian cell;
- exact metric invariance under all discovered operations;
- affine coordinate equivariance;
- covariance under a nontrivial unimodular lattice-basis shear;
- source/digest mismatch rejection and canonical serialization;
- collision rejection;
- coincident projected parallel-edge rejection;
- transactional resource failure;
- straight-segment lifted endpoint and length correctness; and
- Na-LTA construction with the complete 96-operation symmetry group.

# References

[1] S. J. Chung, Th. Hahn, and W. E. Klee, "Nomenclature and generation of
three-periodic nets: the vector method," *Acta Cryst. A* **40**, 42--50 (1984),
doi:10.1107/S0108767384000088.

[2] O. Delgado-Friedrichs, "Equilibrium placement of periodic graphs and convexity
of plane tilings," in *Graph Drawing*, LNCS 2912, 178--189 (2004),
doi:10.1007/978-3-540-24595-7_17.

[3] O. Delgado-Friedrichs and M. O'Keeffe, "Identification of and symmetry
computation for crystal nets," *Acta Cryst. A* **59**, 351--360 (2003),
doi:10.1107/S0108767303012017.
