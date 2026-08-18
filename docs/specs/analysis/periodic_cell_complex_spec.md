---
title: "Periodic Cell Complex and Partition Certificate Specification"
subtitle: "Stage 9: Translation-Labelled Chain Algebra and Exact Periodic Tetrahedral Certification"
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

# Purpose and stage boundary

Stage 9 turns a caller-selected, compatibility-safe set of embedded scientific
faces into a finite periodic cell complex with explicit integer attaching maps.
It then permits a separate exact auxiliary tetrahedral decomposition to certify
that the proposed scientific tiles form a genuine partition of the three-torus.
Runtime/API target:

```text
mdstats 0.19.23a0
```

The stage answers two distinct questions.

1. **Scientific topology:** do the selected face placements and proposed tile
   shells define a valid translation-labelled periodic cell complex?
2. **Geometric partition:** does an explicit periodic tetrahedral mesh prove
   disjoint tile interiors, conforming scientific interfaces, and complete
   coverage of one primitive periodic domain?

The scientific object and the auxiliary proof are deliberately separate:

```text
PeriodicCellComplex != PeriodicPartitionCertificate
```

A different conforming tetrahedralization may certify the same scientific
complex without changing its identity.

Stage 9 does **not** select natural faces, infer tile shells from local sectors,
search for a tetrahedralization, prove properness under the full net symmetry,
or decide whether a unique natural tiling exists. Those are Stage-10
orchestration responsibilities.

# Source contract

The scientific builder consumes mutually consistent instances of:

```text
PeriodicNetView
PeriodicNetEmbedding
PrimitiveRingIndex
FacePlacementCertificate[]
FaceEmbeddingWitness[]
PeriodicTileShell[]
FaceCompatibilityConstraintSystem | None
```

The first backend requires:

- one connected three-periodic net;
- translation rank three;
- translation-subgroup index one;
- `ProjectedEdgeCurveModel.STRAIGHT_SEGMENT`;
- one certified admissible selected witness per scientific face;
- no selected forbidden or unresolved witness tuple; and
- exact agreement of graph, view, embedding, ring-catalog, face, and witness
  identities.

The partition certifier additionally consumes:

```text
AuxiliaryVertexOrbit[]
PeriodicTetrahedron[]
```

Every auxiliary tetrahedron is assigned to one translated placement of one
scientific tile orbit.

# Translation-labelled chain algebra

## Cell placements

Let the quotient contain finite orbit sets $V$, $E$, $F$, and $T$. A physical
cell occurrence is represented by

$$
(c,\mathbf n),\qquad \mathbf n\in\mathbb Z^3,
$$

where $c$ is a quotient-cell index and $\mathbf n$ is a lattice translation.
The public chain term is

```python
TranslatedCellTerm(
    cell_index: int,
    image_shift: tuple[int, int, int],
    coefficient: int,
)
```

Terms with equal `(cell_index, image_shift)` are combined over $\mathbb Z$.
Stored zero coefficients are forbidden.

This follows the labelled finite-graph representation of periodic nets introduced
by Chung, Hahn, and Klee [1]: finite quotient identity is retained together with
integer translation labels. Stage 9 extends that idea from graph edges to the
complete cellular boundary algebra.

## Boundary operators

```python
PeriodicBoundaryOperator(
    source_dimension: Literal[1, 2, 3],
    source_cell_count: int,
    target_cell_count: int,
    columns: tuple[tuple[TranslatedCellTerm, ...], ...],
)
```

Each column is the boundary of one quotient cell. Translation acts by addition:

$$
(c,\mathbf n)+(\text{translate by }\mathbf m)
=(c,\mathbf n+\mathbf m).
$$

Composition multiplies coefficients and adds image shifts. The scientific
complex requires

$$
\partial_1\partial_2=0,
\qquad
\partial_2\partial_3=0.
$$

### Edge boundary

For an oriented quotient edge

$$
e=(i,j,\boldsymbol\delta),
$$

translated by $\mathbf a$,

$$
\partial_1(e,\mathbf a)
=(v_j,\mathbf a+\boldsymbol\delta)
-(v_i,\mathbf a).
$$

Self-image edges are therefore supported directly; $i=j$ does not imply a zero
boundary when $\boldsymbol\delta\ne\mathbf 0$.

### Face boundary

A scientific face is an oriented primitive-ring placement. For each directed ring
step, the implementation resolves the canonical physical edge instance and adds
its orientation multiplied by the face orientation. Hence

$$
\partial_2 f
=\sum_k \sigma_k(e_k,\mathbf a_k),
\qquad \sigma_k\in\{-1,+1\}.
$$

No auxiliary witness triangle appears in scientific face identity or in
$\partial_2$.

### Tile boundary

A caller proposes each tile shell explicitly:

```python
PeriodicTileShell(
    tile_index: int,
    face_incidences: tuple[TranslatedCellTerm, ...],
    label: str = "",
)
```

Every tile-side coefficient must be $\pm1$. The resulting shell is one column of
$\partial_3$.

# Scientific cell-complex invariants

```python
PeriodicCellComplex(
    periodic_net_view_digest: str,
    topology_graph_digest: str,
    periodic_net_embedding_digest: str,
    primitive_ring_catalog_digest: str,
    face_placements: tuple[FacePlacement, ...],
    tile_shells: tuple[PeriodicTileShell, ...],
    boundary_1: PeriodicBoundaryOperator,
    boundary_2: PeriodicBoundaryOperator,
    boundary_3: PeriodicBoundaryOperator,
    tile_shell_invariants: tuple[TileShellInvariant, ...],
    construction_witness_digests: tuple[str, ...],
)
```

Construction is accepted only if all of the following hold.

1. $\partial_1\partial_2=0$.
2. $\partial_2\partial_3=0$.
3. Every scientific face orbit has exactly two translated tile-side incidences.
4. The quotient Euler characteristic is that of the three-torus:

   $$
   N_0-N_1+N_2-N_3=0.
   $$

5. Every lifted tile boundary is connected, nonbranching, orientable, and has
   Euler characteristic two.

## Lifted shell validation

For one tile shell, every translated face boundary is expanded into translated
edge instances. A valid closed orientable shell requires:

- each physical edge instance occurs exactly twice;
- the two signed edge incidences cancel;
- the face-adjacency graph through shared edges is connected; and
- with unique lifted vertex, edge, and face occurrences,

  $$
  \chi_{\partial t}=V-E+F=2.
  $$

Under these finite simplicial/cellular assumptions, the accepted boundary is a
connected orientable nonbranching genus-zero shell. The implementation records:

```python
TileShellInvariant(
    tile_index: int,
    vertex_instance_count: int,
    edge_instance_count: int,
    face_instance_count: int,
    euler_characteristic: int,
    connected: bool,
    nonbranching: bool,
    orientable: bool,
)
```

This check validates the supplied shell. It does not discover which local face
side belongs to which tile.

# Scientific identity and construction provenance

The `PeriodicCellComplex.digest` includes the exact scientific faces, tile shells,
and boundary operators. Auxiliary triangulations are excluded from that
scientific digest. The selected witness digests are retained separately as
construction provenance because the current builder must know that the selected
faces had a simultaneously admissible realization.

Consequently:

- changing a tile attaching map changes scientific identity;
- changing only a conforming auxiliary tetrahedral mesh does not; and
- replay may still verify which witnesses justified the construction.

# Exact periodic tetrahedral certificate

## Auxiliary records

```python
AuxiliaryVertexOrbit(
    vertex_index: int,
    fractional_coordinate: tuple[Fraction, Fraction, Fraction],
)
```

Coordinates are canonical representatives in $[0,1)^3$.

```python
AuxiliaryVertexRef(
    vertex_index: int,
    image_shift: tuple[int, int, int],
)
```

identifies one lifted vertex occurrence.

```python
TilePlacementRef(
    tile_index: int,
    image_shift: tuple[int, int, int],
)
```

identifies one lifted scientific tile occurrence.

```python
PeriodicTetrahedron(
    tetrahedron_index: int,
    vertices: tuple[AuxiliaryVertexRef, AuxiliaryVertexRef,
                    AuxiliaryVertexRef, AuxiliaryVertexRef],
    tile_placement: TilePlacementRef,
)
```

The certifier normalizes each tetrahedron to positive exact orientation. Degenerate
tetrahedra are rejected.

## Broad phase and exact overlap relation

Continuous lifted AABBs are passed to the Stage-8B periodic spatial backend. Its
support-derived translation stencil supplies conservative image-labelled pairs;
no fixed neighbor-image shell is assumed.

Each surviving pair is classified exactly with rational arithmetic. The
separating-axis family contains:

- face normals from both tetrahedra; and
- cross products of every edge direction from the first tetrahedron with every
  edge direction from the second.

This is an exact-arithmetic adaptation of the tetrahedron-overlap/SAT approach
discussed by Ganovelli, Ponchio, and Rocchini [3]. It is not a transcription of
their optimized floating implementation. Robust combinatorial decisions follow
Shewchuk's exact-sign principle [2], here realized directly with
`fractions.Fraction`.

The result is one of:

```text
DISJOINT
BOUNDARY_CONTACT
IMPROPER_INTERIOR_OVERLAP
CONTAINMENT_OVERLAP
COINCIDENT_INTERIOR
```

Only the first two are permitted. Shared facets, edges, and vertices are allowed;
positive-volume interior overlap is forbidden.

Containment is reported only when every vertex of one tetrahedron lies in the
closed other tetrahedron. A partial interpenetration with only some contained
vertices remains `IMPROPER_INTERIOR_OVERLAP`.

# Periodic facet pairing

Every oriented tetrahedron contributes four oriented triangular facets. A facet
is canonicalized modulo a common integer translation of its three lifted vertex
references. Certification requires exactly two tetrahedral incidences per
periodic facet orbit.

After translation into one common lifted frame, the two facets must:

- have exactly equal rational vertex sets; and
- carry opposite induced orientations.

The pair is classified as:

```text
AUXILIARY_INTERNAL
SCIENTIFIC_INTERFACE
```

It is internal when the transformed tetrahedra belong to the same exact
`TilePlacementRef`. Otherwise it is a scientific interface and must match exactly
one triangle orbit of exactly one selected `FaceEmbeddingWitness`.

# Face conformity and induced tile shell

Each scientific face witness may contain several triangles. For every tile side,
the auxiliary interface triangles must cover every triangle of that selected
witness exactly once and with one common face orientation.

The implementation then collapses that complete triangle set to one signed
translated scientific face term. The auxiliary partition is accepted only if the
resulting tile boundary equals the pre-existing scientific $\partial_3$ column
exactly.

This check prevents two common false certifications:

1. an auxiliary mesh covers the right geometric surface but induces a different
   scientific face orientation or image shift; or
2. only part of a multi-triangle scientific face is present on a tile side.

Global reversal of a proposed tile shell is not silently accepted. Tile
orientation is part of its supplied attaching map and must agree with the
positive orientation induced by the certificate tetrahedra.

# Coverage theorem implemented by the certificate

After exact overlap rejection and complete periodic facet pairing, all auxiliary
tetrahedra form a closed periodic pseudomanifold with no unmatched facets. Exact
face conformity assigns every noninternal facet to the declared scientific
interface. Finally, exact oriented tetrahedral volumes are accumulated by tile:

$$
V_t=\sum_{\tau\mapsto t}
\frac{\det(\mathbf x_1-\mathbf x_0,
           \mathbf x_2-\mathbf x_0,
           \mathbf x_3-\mathbf x_0)}{6}.
$$

Certification requires

$$
V_t>0\quad\text{for every tile orbit},
\qquad
\sum_t V_t=1.
$$

Volume closure is used only after exact nonoverlap and closed facet pairing. On
its own, $\sum_tV_t=1$ would not rule out compensating voids and overlaps.

The returned proof record is:

```python
PeriodicPartitionCertificate(
    periodic_cell_complex_digest: str,
    periodic_net_embedding_digest: str,
    auxiliary_vertices: tuple[AuxiliaryVertexOrbit, ...],
    tetrahedra: tuple[PeriodicTetrahedron, ...],
    facet_pairs: tuple[PeriodicFacetPair, ...],
    face_triangle_coverage: tuple[FaceTriangleCoverage, ...],
    overlap_candidate_set_digest: str,
    exact_tetrahedron_test_count: int,
    tile_fractional_volumes: tuple[Fraction, ...],
    total_fractional_volume: Fraction,
)
```

# Algorithms

## Scientific complex construction

```text
validate exact source identities and Stage-9 eligibility
validate one admissible selected witness per face
reject selected forbidden or unresolved compatibility tuples
construct translation-labelled boundary_1 from quotient edges
construct translation-labelled boundary_2 from oriented ring placements
construct boundary_3 from proposed tile shells
verify boundary_1 * boundary_2 == 0
verify boundary_2 * boundary_3 == 0
verify two tile-side incidences per face orbit
verify quotient Euler characteristic == 0
for each tile shell:
    lift all face-boundary edge occurrences
    require two edge incidences and signed cancellation
    require connected face adjacency
    count lifted V, E, F and require V - E + F == 2
return PeriodicCellComplex
```

## Partition certification

```text
validate source complex, embedding, ring index, and selected witnesses
preflight auxiliary vertex, tetrahedron, facet, and exact-test resources
normalize all tetrahedra to positive orientation
build complete periodic AABB candidate set
for every candidate image pair:
    classify exact tetrahedron relation
    reject all interior-overlap relations
canonicalize all oriented tetrahedral facets modulo translation
require exactly two opposite-oriented incidences per facet orbit
for every facet pair:
    if transformed tile placements agree:
        record auxiliary-internal facet
    else:
        match exactly one selected witness triangle orbit
        record scientific interface and orientation
require exact once-only coverage of every witness triangle orbit
collapse complete triangle sets to scientific face-side terms
require the induced shell of every tile to equal scientific boundary_3
sum exact positive tetrahedral volumes by tile
require total volume == 1
return PeriodicPartitionCertificate
```

# Resource model

```python
PeriodicPartitionResources(
    max_auxiliary_vertices: int = 100_000,
    max_tetrahedra: int = 500_000,
    max_exact_tetrahedron_tests: int = 5_000_000,
    max_facet_occurrences: int = 2_000_000,
)
```

Limits are execution controls, not mathematical domain definitions. Size limits
are checked before expensive work where possible. The exact-test counter is
checked before crossing its declared bound. Exceeding a limit raises
`PeriodicCellComplexResourceError`; no partial certificate is returned.

# Serialization and replay

Both principal records use canonical JSON and SHA-256:

```text
mdstats.periodic-cell-complex.v1
mdstats.periodic-partition-certificate.v1
```

`PeriodicCellComplex.from_dict(...)` does not trust serialized boundary matrices
or shell invariants. It parses only the proposed tile shells, rebuilds the entire
scientific complex from the supplied authoritative sources, and requires bytewise
canonical payload equality.

`PeriodicPartitionCertificate.from_dict(...)` parses only the auxiliary vertices,
tetrahedra, and tile assignments, reruns the exact periodic certification, and
requires canonical payload equality.

Thus altering a digest, test count, volume, facet relation, coverage record,
boundary operator, or invariant is rejected rather than accepted as cached truth.

# Error model

```text
PeriodicCellComplexInputError
PeriodicCellComplexInvariantError
PeriodicCellComplexResourceError
PeriodicCellComplexSerializationError
```

Typical input errors include mixed source digests, ineligible periodic nets,
invalid dense indices, invalid shifts, nonadmissible selected witnesses, and tile
references outside the proposed complex.

Invariant errors include failed chain identities, nonmanifold or nonspherical tile
shells, wrong face incidence multiplicity, tetrahedral interior overlap, unmatched
facets, nonconforming interfaces, induced-shell mismatch, and failed exact volume
closure.

# Edge cases and explicit limitations

- **Self-image graph incidence:** supported through translation-labelled edge
  boundaries.
- **Self-image tile faces:** supported; the two incidences may belong to translated
  placements of the same tile orbit.
- **Boundary contact between tetrahedra:** allowed when exact interiors are
  disjoint.
- **Coplanar coincident tetrahedra:** rejected as coincident interior.
- **Partial tetrahedral interpenetration:** rejected as improper overlap, not
  mislabeled as containment.
- **Different witness triangulation:** allowed only when the supplied auxiliary
  mesh conforms to that exact selected witness.
- **Automatic tetrahedralization:** not implemented.
- **Curved projected edges or faces:** not implemented in the first backend.
- **Disconnected or lower-dimensional periodic nets:** rejected.
- **Local face-sector shell discovery:** deferred; callers supply shells.
- **Naturalness, properness, symmetry orbit pruning, and uniqueness:** deferred to
  Stage 10.
- **General polyhedral overlap without tetrahedral auxiliary decomposition:** not
  implemented.
- **Floating coordinate input:** scientific certification expects exact rational
  coordinates from the authoritative embedding and explicit auxiliary records.

# Focused validation requirements

The Stage-9 gate must include:

1. exact classification of disjoint, boundary-contact, coincident, containment,
   and partial-overlap tetrahedron pairs;
2. a periodic simple-cubic quotient with cell counts $(1,3,3,1)$;
3. nonzero translation labels and self-image edge incidence;
4. exact $\partial_1\partial_2=0$ and $\partial_2\partial_3=0$;
5. connected orientable nonbranching tile boundary with $\chi=2$;
6. rejection of a sign-corrupted open shell;
7. rejection of a selected unresolved face assignment;
8. exact certification of the six-tetrahedron Freudenthal/Kuhn subdivision of one
   unit cube;
9. rejection of coincident tetrahedral interiors;
10. rejection of a nonconforming face triangulation;
11. rejection of incomplete periodic facet pairing;
12. transactional resource failure; and
13. source-replay acceptance plus tamper rejection for both principal records.

# References

[1] S. J. Chung, Th. Hahn, and W. E. Klee, “Nomenclature and generation
of three-periodic nets: the vector method,” *Acta Crystallographica Section A*
**40**, 42--50 (1984). doi:10.1107/S0108767384000088.

[2] J. R. Shewchuk, “Adaptive Precision Floating-Point Arithmetic and Fast
Robust Geometric Predicates,” *Discrete & Computational Geometry* **18**,
305--363 (1997). doi:10.1007/PL00009321.

[3] F. Ganovelli, F. Ponchio, and C. Rocchini, “Fast Tetrahedron--Tetrahedron
Overlap Algorithm,” *Journal of Graphics Tools* **7**(2), 17--25 (2002).
doi:10.1080/10867651.2002.10487557.
