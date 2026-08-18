---
title: "LTA Natural-Tiling Ground-Gate Specification"
subtitle: "Stage 10D: Exact Face Selection, Tile-Side Propagation, Convex Periodic Partition, and Bound Stability"
author: "mdstats"
date: "2026-07-19"
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

Stage 10D is the first end-to-end scientific ground gate for natural tilings. It
certifies the natural tiling of the **unlabeled LTA framework net** at primitive
ring bounds

$$
K\in\{8,10,12\}.
$$

The expected finite lifted tile types are

$$
[4^6],\qquad [4^6.6^8],\qquad [4^{12}.6^8.8^6],
$$

with primitive-cell multiplicities

$$
6:2:2=3:1:1.
$$

Runtime/API target:

```text
mdstats 0.19.27a0
```

Primary module:

```text
mdstats/analysis/lta_natural_tiling.py
```

The backend is intentionally **LTA-specific**. It is not promoted as a generic
master-refinement constructor. It accepts only the exact unlabeled LTA quotient
fingerprint and the complete validation sequence `(8, 10, 12)`.

# Scientific motivation

Stages 8C--10C supply the independent machinery required for natural tilings:
embedded ring faces, translation-labelled cell complexes, partition evidence,
properness, bounded face selection, and cross-bound comparison. None of those
stages alone proves that the implementation recovers the published LTA natural
tiling.

LTA is a strong end-to-end gate because increasing the ring bound from 8 to 12
introduces 32 additional primitive 12-rings. Those rings are boundedly strong in
the active depth-one domain, so a gate that selects faces from strength alone
would change the tiling incorrectly. The authoritative exact embedding provides
the missing geometric distinction: all 32 new 12-rings are nonplanar and cannot
be scientific 2-cells in the first planar-face backend.

# External methods and original construction

The periodic quotient and translation-labelled cycle convention is compatible
with the vector method of Chung, Hahn, and Klee [1]. The natural-tiling target and
properness requirement follow Blatov, Delgado-Friedrichs, O'Keeffe, and Proserpio
[2]. Exact sign decisions use rational arithmetic in the spirit of robust
predicate design.

The following Stage-10D mechanisms are project-specific `mdstats` constructions:

- strict-convex-planar filtering of bounded-strong primitive rings in the
  authoritative rational embedding;
- exact cyclic sorting of incident face-interior rays in the quotient plane
  normal to a framework edge;
- translation-labelled face-side propagation into finite lifted tile shells;
- a convex-polytope periodic partition certificate based on exact supporting
  halfspaces, volumes, and separating axes;
- generator-based properness certification after exact replay of full-group
  closure; and
- proof-preserving reuse across larger $K$ only after exact selected-ring stable
  keys are unchanged.

# Input contract

## Required topology

```python
certify_lta_natural_tiling(
    topology: FrameworkTopology,
    *,
    bounds: Sequence[int] = (8, 10, 12),
    resources: LtaNaturalTilingResources | None = None,
) -> LtaNaturalTilingGate
```

The first backend requires:

- one connected, rank-three, translation-index-one periodic net;
- 48 quotient vertices;
- 96 quotient edges;
- degree four at every quotient vertex;
- a complete exact unlabeled automorphism group of order 96; and
- the exact bound sequence `(8, 10, 12)`.

A topology that merely has the expected ring counts is not accepted. Source
identity, periodic rank, quotient size, degree sequence, and complete symmetry
must all agree.

## Finite resources

`LtaNaturalTilingResources` bounds:

- number of tested bounds;
- primitive rings per bound;
- selected scientific faces;
- exact fan self-intersection tests;
- exact framework--triangle contact tests;
- edge-sector incidences;
- periodic tile-image pairs;
- exact separating-axis tests;
- generator face and tile images; and
- generator-closure multiplication checks.

A resource failure raises `LtaNaturalTilingResourceError`; it is never converted
into a scientific rejection.

# Bound rebuild and stable reuse

For every $K$, Stage 10D independently rebuilds:

```text
primitive rings
-> source-bound ring index
-> depth-one bounded strength
-> exact ring polygon geometry
-> selected scientific ring keys
```

At $K=8$, the complete downstream stack is certified:

```text
selected faces
-> embedded fan witnesses
-> exact edge-sector propagation
-> translation-labelled cell complex
-> full-group properness
-> convex periodic partition
```

For $K=10$ and $12$, downstream evidence may be reused only after the new build
proves byte-for-byte equality of the ordered selected `PrimitiveRingKey` digests.
This is proof-preserving memoization, not stale source-object reuse. The higher
bound has already independently rebuilt every stage that could introduce or
remove a scientific face. The deterministic downstream construction depends only
on:

- the fixed exact net view;
- the fixed authoritative embedding;
- the complete fixed automorphism group; and
- the exact selected ring-key set.

If those keys differ, the backend must perform a new downstream certification or
reject the ground-gate assumption.

# Bounded ring strength

For every primitive ring $R$ of size $n$, the active domain is

```python
RingStrengthDomain(
    target_ring_key=R.key,
    max_component_size=n - 1,
    placement_domain=EdgeIncidencePlacementDomain(1),
)
```

This tests decompositions into strictly smaller represented primitive rings whose
placements lie within one exact edge-incidence step of the target.

Expected counts are:

| Bound | Ring size | Strong in domain | Weak certified |
|---:|---:|---:|---:|
| 8 | 4 | 36 | 0 |
| 8 | 6 | 16 | 24 |
| 8 | 8 | 6 | 0 |
| 10 | same as 8 | same | same |
| 12 | 12 | 32 | 0 |

Strength is necessary but not sufficient for face selection.

# Exact ring-polygon geometry

For a canonical lifted ring walk with exact fractional coordinates

$$
\mathbf p_0,\ldots,\mathbf p_{n-1},
$$

Stage 10D first finds two independent in-plane vectors

$$
\mathbf u=\mathbf p_i-\mathbf p_0,
\qquad
\mathbf v=\mathbf p_j-\mathbf p_0.
$$

Coplanarity requires

$$
\det\!\left(\mathbf u,\mathbf v,
\mathbf p_k-\mathbf p_0\right)=0
\qquad\text{for every }k.
$$

An injective coordinate pair is then chosen from a nonzero $2\times2$ minor of
$[\mathbf u\;\mathbf v]$. Every consecutive projected turn must be nonzero and
have the same sign. The resulting states are:

```text
STRICTLY_CONVEX_PLANAR
NONPLANAR
PLANAR_NONCONVEX_OR_DEGENERATE
```

A scientific face is selected exactly when

```text
strength == STRONG_IN_DOMAIN
and geometry == STRICTLY_CONVEX_PLANAR
```

Expected selected faces at all three bounds are:

$$
36\times4\mathrm R,
\qquad16\times6\mathrm R,
\qquad6\times8\mathrm R.
$$

At $K=12$, the 32 new strong 12-rings are explicitly retained as
`strong-but-nonplanar` exclusions.

# Embedded face witnesses

Every selected strict convex planar $n$-gon uses the canonical fan

$$
(0,1,2),(0,2,3),\ldots,(0,n-2,n-1).
$$

The backend verifies:

- nondegenerate exact triangles;
- no forbidden zero-image fan self-intersection;
- no forbidden periodic self-image intersection; and
- no framework-edge penetration other than the exact boundary edge or shared
  boundary vertex allowed by Stage 8C.

Unlike the general Stage-8C backend, Stage 10D does not enumerate every Catalan
triangulation. Strict convex planarity proves that the canonical fan is an
embedded disk in its supporting plane. Exact periodic and framework-contact tests
supply the remaining global checks.

# Exact face-side propagation

## Incident face rays

For one lifted framework edge with direction $\mathbf d$ and midpoint
$\mathbf m$, every incident selected face placement supplies a ray

$$
\mathbf r=\mathbf c_F-\mathbf m,
$$

where $\mathbf c_F$ is the exact average of the lifted face vertices.

Choose a nonzero component $d_k$ and the remaining axes $a,b$. A quotient-plane
coordinate is

$$
q(\mathbf r)=
\left(
 d_k r_a-d_a r_k,
 d_k r_b-d_b r_k
\right),
$$

with one deterministic sign calibration so that the 2D cross-product order agrees
with the 3D determinant

$$
\det(\mathbf d,\mathbf r_i,\mathbf r_j).
$$

Every LTA framework edge must have exactly three distinct incident selected-face
rays.

## Side adjacency and voltage gain

Consecutive cyclic rays define one local tile sector. For consecutive ring-edge
occurrences $A$ and $B$, Stage 10D joins the oriented face-side states

$$
(F_A,s_A)
\longleftrightarrow
(F_B,-s_B)
$$

with translation gain

$$
\mathbf g=\mathbf t_B-\mathbf t_A.
$$

Translation offsets are propagated through each connected face-side component.
A repeated node with a different accumulated offset proves a nonzero voltage
cycle and rejects a slab, channel, or other noncompact region.

Each zero-gain component yields one finite lifted tile shell. If a component
contains side state $(F,s)$ at propagated translation $\mathbf t$, its boundary
term is

$$
-s\,[F,\mathbf t].
$$

# Translation-labelled cell complex

The 58 selected face orbits and ten propagated tile shells are passed to Stage 9.
The exact complex must have

$$
(N_0,N_1,N_2,N_3)=(48,96,58,10),
$$

and satisfy

$$
\partial_1\partial_2=0,
\qquad
\partial_2\partial_3=0,
\qquad
48-96+58-10=0.
$$

Every face has exactly two translated tile-side incidences. Every lifted tile
boundary is connected, nonbranching, orientable, and genus zero.

# Properness from exact generators

The complete symmetry discovery stores a certified finite group $G$ of order 96
and a reduced generator set $S$. Stage 10D independently replays closure of $S$
under the stored multiplication table and requires

$$
\langle S\rangle=G.
$$

For every generator, the implementation maps every scientific face placement and
every translation-labelled tile shell. If each generator preserves the complete
scientific complex, every word in the generators preserves it; therefore every
net automorphism preserves the tiling.

Because the tiling uses the fixed net as its 1-skeleton, this proves

$$
\operatorname{Aut}(\mathcal T)
=
\operatorname{Aut}(G_{\mathrm{view}}).
$$

Auxiliary fan triangles and convex-partition support data do not participate in
properness.

# Exact convex periodic partition certificate

## Convexity and interior points

For one tile shell, every oriented face supplies an outward plane

$$
\mathbf n_F\cdot(\mathbf x-\mathbf p_F)\le0.
$$

Every lifted tile vertex must satisfy every halfspace. The exact average of the
distinct tile vertices must satisfy all inequalities strictly and is stored as an
interior witness.

## Exact volume

Each oriented polygon is triangulated by its fan. The signed fractional volume is

$$
V_T=\frac{1}{6}\sum_{(\mathbf a,\mathbf b,\mathbf c)}
\mathbf a\cdot(\mathbf b\times\mathbf c).
$$

Every tile volume must be positive and

$$
\sum_T V_T=1.
$$

For LTA, the exact per-tile volumes are:

| Tile type | Multiplicity | Fractional volume |
|---|---:|---:|
| $[4^6]$ | 6 | $1/256$ |
| $[4^6.6^8]$ | 2 | $61/768$ |
| $[4^{12}.6^8.8^6]$ | 2 | $157/384$ |

## Periodic interior-disjointness

For every pair of tile orbits and every integer translation whose exact AABBs can
overlap, the certificate applies the convex-polytope separating-axis family:

- every face normal of either polytope; and
- every nonzero cross product of one edge direction from each polytope.

An axis $\mathbf a$ separates interiors when

$$
\max_{x\in A}\mathbf a\cdot x
\le
\min_{y\in B+\mathbf t}\mathbf a\cdot y
$$

or the reversed inequality holds. Equality permits a shared boundary. If no axis
separates a candidate pair, the construction is rejected as an interior overlap.

Pairwise periodic interior-disjointness plus exact total volume one excludes an
open positive-measure void in the unit three-torus. This implication is used only
after convexity and all periodic image candidates have been certified.

# Persistent result model

```python
LtaNaturalTilingGate(
    topology_graph_digest=...,
    periodic_net_view_digest=...,
    periodic_net_symmetry_digest=...,
    periodic_net_embedding_digest=...,
    bounds=(8, 10, 12),
    observations=(...),
    expected_tile_multiplicities=(...),
    selected_faces_stable=True,
    tiling_stable=True,
    expected_lta_match=True,
    status=LtaNaturalTilingGateStatus.CERTIFIED,
)
```

Each `LtaBoundObservation` records:

- primitive-ring counts by size;
- strength counts by size and state;
- exact geometry counts by size and state;
- selected face counts and stable ring-key digests;
- strong-but-nonplanar exclusions;
- cell counts;
- tile signatures and multiplicities;
- reduced multiplicity ratio;
- mesh-independent scientific complex key;
- exact convex partition volume, pair, and axis summaries; and
- full-group properness status.

`to_dict()` uses canonical JSON-compatible payloads and SHA-256 digests.
`from_dict()` deterministically replays the complete gate against the supplied
`FrameworkTopology` and rejects altered evidence.

# Certification outcome

The gate is `CERTIFIED` only when all three bounds satisfy:

1. selected scientific ring keys are identical;
2. the mesh-independent scientific tile complex is identical;
3. cell counts are $(48,96,58,10)$;
4. tile multiplicities are $6,2,2$ in the expected signature order;
5. the reduced ratio is $3:1:1$;
6. exact convex periodic partition certification succeeds; and
7. the complete unlabeled net automorphism group preserves the tiling.

Any proved mismatch is `REJECTED`. A future generalized backend may return
`UNRESOLVED` for bounded or unsupported cases; the present strict ground gate
raises explicit input/resource errors before constructing a misleading result.

# Edge cases and failure policy

The implementation rejects:

- any bound sequence other than `(8, 10, 12)`;
- a non-LTA quotient fingerprint;
- incomplete or non-order-96 symmetry;
- an uncertified straight-edge embedding;
- selected faces with nonplanarity, degeneracy, self-intersection, or framework
  penetration;
- an edge with other than three distinct selected face sectors;
- nonzero translation cycles in a putative tile component;
- a cell complex that violates chain, incidence, Euler, or shell invariants;
- a generator image outside the selected face or tile set;
- nonconvex tile shells;
- nonpositive or nonclosing exact tile volumes;
- periodic tile interior overlap; and
- altered persistent digests or replay payloads.

# Focused validation requirements

The Stage-10D focused gate must verify:

- complete certification at $K=8,10,12$;
- ring counts $82,82,114$;
- 32 new nonplanar 12-rings at $K=12$;
- stable selected faces $36\times4\mathrm R$, $16\times6\mathrm R$,
  $6\times8\mathrm R$;
- tile counts $6,2,2$ and ratio $3:1:1$;
- exact cell counts $(48,96,58,10)$;
- exact tile volumes and total volume one;
- periodic SAT candidate and axis audit counts;
- generator closure and scientific-complex preservation;
- resource preflight;
- exact bound-sequence rejection; and
- digest tamper rejection.

# Limitations and next boundary

Stage 10D proves the expected LTA result under one exact, strict-convex-planar
first backend. It does not yet:

- construct a generic master refinement from arbitrary strong rings;
- resolve nonplanar or multiply embedded face surfaces;
- search alternative witness families;
- recognize arbitrary nets as LTA up to unrestricted periodic isomorphism;
- prove stabilization for every $K>12$; or
- convert tiles automatically into physical cages, portals, and accessibility
  networks.

The next implementation boundary is Stage 11: tile geometry, cage identity,
windows/portals, and chemistry-aware accessibility built on the now-certified LTA
natural tiling.

# References

[1] S. J. Chung, T. Hahn, and W. E. Klee, "Nomenclature and generation of
three-periodic nets: the vector method", *Acta Crystallographica A* **40**, 42--50
(1984). doi:10.1107/S010876738400010X.

[2] V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M. Proserpio,
"Three-periodic nets and tilings: natural tilings for nets", *Acta
Crystallographica A* **63**, 418--425 (2007).
doi:10.1107/S0108767307038287.
