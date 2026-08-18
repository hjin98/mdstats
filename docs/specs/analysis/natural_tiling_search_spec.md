---
title: "Natural Face Selection and Master-Refinement Splitting Specification"
subtitle: "Stage 10B: Symmetry-Closed Strong-Ring Cuts, Exact Periodic Coarsening, and Maximal Alternatives"
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

Stage 10B generates natural-tiling candidates from one exact, caller-supplied
**master refinement**. The master refinement is a Stage-9 periodic cell complex
and tetrahedral partition containing every ring surface admitted to the finite
search. Stage 10B then:

1. computes full-symmetry orbits of the master scientific faces;
2. admits only orbits whose rings are `STRONG_IN_DOMAIN`;
3. enumerates every nonempty symmetry-closed subset within explicit bounds;
4. prunes forbidden or unresolved fixed-witness combinations;
5. merges tetrahedra across omitted interfaces;
6. rejects lifted components with nonzero translation cycles;
7. reconstructs exact translation-labelled tile shells;
8. re-certifies the resulting periodic partition;
9. applies Stage-10A properness and candidate certification; and
10. retains every inclusion-maximal valid splitting without an enumeration-order
    tie-break.

Runtime/API target:

```text
mdstats 0.19.25a0
```

Primary module:

```text
mdstats/analysis/natural_tiling_search.py
```

Stage 10B does **not** infer the master tetrahedral refinement, introduce arbitrary
Steiner surfaces, search alternative triangulations inside one run, prove global
unbounded ring strength, refine the primitive-ring bound, or certify the LTA
end-to-end result. Those responsibilities remain explicit upstream inputs or
Stages 10C--10D.

# Motivation

Stage 10A can certify a proposed periodic cell complex, but it cannot generate one.
A direct generator based on local face-sector propagation would require a
completeness theorem that is not yet established for the full periodic,
self-image, and crossing-ring setting. Implementing such a heuristic as if it were
complete would create false uniqueness claims.

Stage 10B therefore uses an independently certified finite arrangement. The
master tetrahedral partition already proves:

- complete periodic volume coverage;
- disjoint tetrahedral interiors;
- exact periodic facet pairing;
- exact conformity of every master scientific interface to its selected Stage-8C
  witness; and
- exact translation-labelled master tile shells.

Every searched tiling is a **coarsening** of this arrangement. Removing a master
interface merges the two adjacent tetrahedral regions; keeping it preserves a
ring cut. This makes the finite search exact relative to the supplied arrangement
and avoids an unproved geometric propagation rule.

# External method and original construction

The scientific natural-tiling principles are adapted from Blatov,
Delgado-Friedrichs, O'Keeffe, and Proserpio [1]: preserve the full net symmetry,
use locally strong ring faces, split along admissible non-face strong rings, and
retain legitimate crossing alternatives.

The following parts are project-specific `mdstats` constructions:

- use of one exact Stage-9 master refinement as the finite search domain;
- translation-labelled tetrahedron adjacency for interface removal;
- the zero-voltage-cycle criterion for finite lifted tile components;
- exact reconstruction of tile attaching maps from master interface orientation;
- re-certification of every generated coarsening with the Stage-9 partition
  certifier;
- maximal valid splitting over the finite strong-orbit family; and
- separation of search completeness from the Stage-10A candidate catalog.

The translation-labelled adjacency representation is compatible with the periodic
vector-graph formalism of Chung, Hahn, and Klee [2], but the coarsening proof and
API are derived here.

# Scientific definitions

## Master refinement

A **master refinement** is a pair

$$
(\mathcal C_M,\,\Pi_M),
$$

where $\mathcal C_M$ is a valid `PeriodicCellComplex` and $\Pi_M$ is a valid
`PeriodicPartitionCertificate` for that exact complex. Every face orbit in
$\mathcal C_M$ is a possible cut in the finite Stage-10B search.

The first backend uses the witness assignment already certified by $\Pi_M$.
Alternative witness geometries require separate master refinements. This is a
scientific boundary, not an implementation accident: a tetrahedral arrangement
conforming to one disk witness need not conform to another.

## Symmetry-closed face orbit

Let $\Gamma=\operatorname{Aut}(G_{\mathrm{view}})$ be the complete exact group
from Stage 7R. For a master face representative $f_i$, its orbit is

$$
\mathcal O(i)=\{g\cdot f_i\mid g\in\Gamma\},
$$

where equality is scientific face-orbit equality modulo the exact translated and
oriented Stage-10A action. A selectable face set is a union of complete
$\mathcal O(i)$.

No approximate Cartesian symmetry is used.

## Bounded local strength

A face orbit is selectable only when every represented ring has status

```text
STRONG_IN_DOMAIN
```

in the supplied source-bound `RingStrengthCatalog`.

A certified weak orbit is excluded. A missing, truncated, or source-incomplete
strength result makes the Stage-10B search `UNRESOLVED`; it is not silently treated
as weak and is not available as a certified splitter.

## Fixed-witness compatibility

For one selected face set $F$, the master witness assignment is

$$
A_F=\{(f,w_f): f\in F\}.
$$

A hard unary, pairwise, or higher-order constraint whose complete assignment set
is contained in $A_F$ rejects that selection. An active `UNRESOLVED` constraint
makes the finite search unresolved and prevents construction of that selection.

Constraints involving an omitted face are irrelevant to that selection.

## Exact coarsening graph

Let each master tetrahedron orbit be a quotient vertex. Every paired tetrahedral
facet contributes an undirected adjacency with an exact lattice translation.
Choose the orientation

$$
i@\mathbf 0 \longleftrightarrow j@\boldsymbol\tau,
$$

where $j@\boldsymbol\tau$ is the periodic image whose facet coincides with the
facet of $i@\mathbf 0$.

For a selected scientific face set $F$:

- every auxiliary-internal facet remains an adjacency;
- every scientific interface whose face is omitted from $F$ becomes an adjacency;
- every scientific interface whose face is retained in $F$ is removed from the
  merge graph.

Connected components of the lifted adjacency graph are candidate tile interiors.

## Finite lifted-component criterion

During quotient traversal assign every reached tetrahedron orbit $j$ an offset
$\mathbf s_j$ relative to a component root. Along an adjacency
$i@\mathbf 0\leftrightarrow j@\boldsymbol\tau$,

$$
\mathbf s_j=\mathbf s_i+\boldsymbol\tau.
$$

If traversal reaches the same quotient tetrahedron orbit with a different offset,
then a closed quotient walk carries nonzero net translation:

$$
\sum_{e\in W}\boldsymbol\tau_e\ne \mathbf 0.
$$

The lifted component is then periodically unbounded. It represents a slab,
channel, or other percolating region rather than a finite tile, and the selection
is rejected as `NONCOMPACT_TILE_COMPONENT`.

Conversely, if every repeated quotient vertex receives the same offset, every
closed walk has zero translation. The connected quotient component lifts to
translation copies of one finite component containing exactly the propagated
representatives. This establishes the first-backend finite-tile criterion.

## Final tile placement

If tetrahedron orbit $i$ is reached at offset $\mathbf s_i$ in final component
$c$, the stored zero-image tetrahedron belongs to tile placement

$$
(c,-\mathbf s_i).
$$

For an omitted interface, the propagation equation guarantees that the two paired
tetrahedra receive the same translated tile placement. For a selected interface,
they must receive different translated tile placements; otherwise the retained
surface is nonseparating and the selection is rejected.

## Shell reconstruction

Each retained master interface facet has:

- a master scientific face index;
- a face image shift $\mathbf n_f$;
- a witness-triangle index;
- a left-side orientation sign $\epsilon\in\{-1,+1\}$ inherited from the
  master $\partial_3$; and
- the opposite sign on the right side.

For a final tile placement $(c,\mathbf n_c)$, the face incidence is

$$
\epsilon\,[f,\mathbf n_f-\mathbf n_c].
$$

All auxiliary triangles belonging to one complete face side must:

- cover every triangle of the selected witness exactly once;
- carry one common orientation sign; and
- produce one translated scientific face term.

The resulting shells are passed to `build_periodic_cell_complex()`, which again
verifies chain closure, two-sided face incidence, quotient Euler closure, and
connected orientable nonbranching genus-zero tile boundaries.

## Exact partition replay

The master tetrahedron geometry is unchanged. Only its scientific tile placement
is reassigned. The generated complex is then submitted to
`certify_periodic_tetrahedral_partition()` with the reassigned tetrahedra.

Therefore every surviving candidate independently re-proves:

- disjoint tetrahedral interiors;
- complete periodic facet pairing;
- exact selected-face witness conformity;
- exact equality of the induced and scientific $\partial_3$;
- positive tile volumes; and
- exact total fractional volume one.

Volume closure alone is never used as a partition proof.

## Maximal splitting

Let $S$ be the finite set of viable symmetry-orbit selections. A selection
$F\in S$ survives the natural splitting rule only when no strict viable superset
exists:

$$
\nexists F'\in S\quad F\subsetneq F'.
$$

This implements "split along every admissible non-face strong ring" relative to
the master refinement. Multiple incomparable maximal selections remain explicit.
Enumeration order is never a scientific tie-breaker.

# Source contract

The public search function is:

```python
search_natural_tilings_from_master_refinement(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    strength_catalog: RingStrengthCatalog,
    face_certificates: Sequence[FacePlacementCertificate],
    master_witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem,
    master_complex: PeriodicCellComplex,
    master_partition: PeriodicPartitionCertificate,
    *,
    resources: NaturalTilingSearchResources | None = None,
    symmetry_resources: NaturalTilingSymmetryResources | None = None,
    partition_resources: PeriodicPartitionResources | None = None,
) -> NaturalTilingSearchResult
```

All sources must share exact digests for:

- `PeriodicNetView`;
- topology graph;
- periodic net embedding;
- primitive-ring catalog;
- complete net symmetry and induced ring action;
- master scientific complex; and
- master partition certificate.

The face certificates and master witnesses are reordered by scientific face digest
to the master complex order. Their witness digests must exactly equal
`master_complex.construction_witness_digests`.

The compatibility system must cover exactly the master face certificates and must
contain every master witness assignment.

The master complex itself must be invariant under the complete exact net group.
A merely supplied subgroup is insufficient.

# Data model

## `NaturalTilingSearchResources`

```python
NaturalTilingSearchResources(
    max_face_orbits: int = 24,
    max_face_selections: int = 1_000_000,
    max_connectivity_arcs: int = 5_000_000,
    max_candidate_constructions: int = 1_000_000,
)
```

These are execution bounds, not scientific definitions. The face-selection family
is preflighted as

$$
2^m-1,
$$

where $m$ is the number of certified-strong face orbits.

Resource overflow raises `NaturalTilingSearchResourceError` transactionally; no
partial result is published.

## `NaturalFaceOrbit`

Stores:

- dense `orbit_index`;
- master face indices and digests;
- represented primitive-ring keys;
- `STRONG_SELECTABLE`, `WEAK_EXCLUDED`, or `UNRESOLVED`; and
- canonical digest.

## `NaturalFaceSelection`

Stores one nonempty symmetry-closed selection:

- selected face-orbit indices;
- selected master face indices;
- scientific face digests;
- fixed master witness digests; and
- canonical digest.

The selection digest is independent of candidate construction order.

## `NaturalTilingSearchCandidate`

Binds:

```text
NaturalFaceSelection
PeriodicCellComplex
PeriodicPartitionCertificate
NaturalTilingCandidate
```

The Stage-10A candidate must refer to the generated complex, and the exact
partition certificate must certify that same complex.

## `NaturalTilingSearchRejection`

Machine-readable kinds are:

```text
EMPTY_SELECTION
FORBIDDEN_COMPATIBILITY
UNRESOLVED_COMPATIBILITY
NONCOMPACT_TILE_COMPONENT
NONSEPARATING_SELECTED_FACE
INVALID_CELL_COMPLEX
INVALID_PARTITION
INELIGIBLE_CERTIFICATION
NONMAXIMAL_SPLITTING
```

The empty set is not enumerated by the public backend, so `EMPTY_SELECTION` is
reserved for compatible future callers and persistence compatibility.

## `NaturalTilingSearchResult`

Stores:

- all source digests;
- exact face-orbit partition and strength states;
- attempted, compatible, and constructed selection counts;
- maximal generated candidates;
- all rejection diagnostics;
- `COMPLETE` or `UNRESOLVED` search status;
- unresolved reasons; and
- the Stage-10A `NaturalTilingCatalog` over maximal candidates.

`result.certified_catalog` returns the catalog only when the finite search is
complete. A catalog may contain individually eligible Stage-10A candidates while
the Stage-10B search remains unresolved because an omitted face orbit has unknown
strength. Such a catalog is conditional and must not be presented as the certified
natural-tiling answer.

# Algorithm

```text
validate all source identities
validate master face/witness binding
prove master complex is invariant under the full exact net group

compute master face orbits under the full scientific face action
classify each orbit from the bounded strength catalog
mark the search unresolved if any orbit has unresolved strength

selectable_orbits = every STRONG_SELECTABLE orbit
preflight 2^m - 1 selections

for each nonempty subset of selectable_orbits:
    expand to all master faces in those orbits
    apply the fixed master witness assignment

    if a hard compatibility constraint is active:
        reject the selection
        continue

    if an unresolved compatibility constraint is active:
        record unresolved selection
        continue

    remove selected interfaces from the tetrahedron merge graph
    traverse the remaining translation-labelled adjacency

    if one quotient tetrahedron receives inconsistent image offsets:
        reject as a noncompact lifted component
        continue

    assign each tetrahedron to a translated final tile placement
    reconstruct every retained scientific face side

    if a retained face is nonseparating:
        reject
        continue

    build and validate the scientific periodic cell complex
    re-certify the exact tetrahedral partition
    run Stage-10A candidate and properness certification

    if Stage 10A rejects the candidate:
        reject
    else:
        retain as viable

remove every viable selection that is a strict subset of another viable selection
preserve all incomparable maximal selections
build NaturalTilingCatalog from the maximal Stage-10A candidates
publish COMPLETE only if no unresolved strength or compatibility remains
```

# Complexity

Let:

- $m$ be the number of certified-strong face orbits;
- $N_T$ be the number of master tetrahedron orbits;
- $N_F$ be the number of paired tetrahedral facet orbits; and
- $Q$ be the cost of one Stage-9 exact partition re-certification.

The explicit selection family has size

$$
2^m-1.
$$

For one selection, translation-labelled component reconstruction is

$$
O(N_T+N_F).
$$

Shell reconstruction is linear in the selected interface-facet coverage. The
worst-case finite search is therefore

$$
O\!\left((2^m-1)(N_T+N_F+Q)\right).
$$

Full net symmetry is used before construction, so $m$ counts face **orbits**, not
individual face representatives. Compatibility is also checked before exact
partition replay.

# Failure and edge cases

## Noncompact slab or channel

Omitting a necessary periodic cut may create a quotient cycle with nonzero
translation. This is rejected before cell-complex construction. A cubic fixture
with only two coordinate-plane face orbits selected produces an infinite periodic
slab and is correctly rejected.

## Nonseparating selected surface

A selected face may have its two sides connected through omitted interfaces, so
both sides belong to the same translated tile placement. The surface is then not a
valid tile boundary in that coarsening and is rejected.

## Weak ring face

A `WEAK_CERTIFIED` master face orbit is excluded before selection enumeration. It
cannot become essential merely because it appears in the master refinement.

## Unresolved strength

A truncated or source-incomplete orbit is not selectable as a certified splitter.
The search status becomes `UNRESOLVED`; surviving candidates are conditional.

## Crossing alternatives

Hard incompatibility constraints prune impossible simultaneous cuts. Distinct
incomparable maximal selections survive as multiple alternatives. An unresolved
crossing constraint keeps the search unresolved.

The first backend uses one fixed witness assignment from the master refinement.
Alternative witness arrangements require separate exact master refinements and
must not be conflated by enumeration order.

## Invalid shell topology

A finite tetrahedral component can still induce a disconnected, branched,
nonorientable, or positive-genus boundary. `build_periodic_cell_complex()` rejects
it exactly.

## Partition mismatch

Any missing witness triangle, repeated face-side triangle, inconsistent orientation,
improper tetrahedron overlap, facet mismatch, induced-shell mismatch, or volume
failure is rejected by Stage 9.

# Persistence and reproducibility

Canonical schema:

```text
mdstats.natural-tiling-search.v1
```

Digest algorithm:

```text
sha256-canonical-json-v1
```

Every persistent orbit, selection, candidate, and search result has a canonical
digest. `NaturalTilingSearchResult.from_dict()` does not trust stored counters,
rejections, generated complexes, partition certificates, or catalog outcomes. It
replays the complete finite search from the supplied sources and requires exact
canonical equality.

Changing any of the following invalidates reuse:

- net view or topology graph;
- symmetry discovery or ring action;
- periodic embedding;
- primitive-ring catalog or strength results;
- face certificates or master witness assignment;
- compatibility constraints;
- master scientific complex;
- master partition certificate; or
- resource policy when replay requires a smaller bound.

# Focused validation requirements

The Stage-10B gate includes:

1. full cubic symmetry collapsing three coordinate faces to one orbit;
2. axis-labelled cubic symmetry producing three independent face orbits;
3. exhaustive enumeration of all seven nonempty orbit subsets;
4. exact rejection of six noncompact slab/channel selections;
5. unique reconstruction of the closed cubic tiling;
6. certified weak-orbit exclusion before enumeration;
7. unresolved strength propagation to search status;
8. hard higher-order crossing-constraint pruning;
9. unresolved compatibility preservation;
10. transactional face-selection resource preflight;
11. exact master witness binding;
12. preservation of incomparable maximal alternatives;
13. deterministic repeatability; and
14. source-replay tamper rejection.

The same focused Stage-4--10A regression boundary must remain green.

# Explicit non-responsibilities

Stage 10B does not:

- construct the master tetrahedral refinement automatically;
- prove that the supplied refinement contains every geometrically possible face;
- search arbitrary Steiner vertices or PL disks;
- enumerate alternative witnesses within one master refinement;
- infer local face sectors without independent partition evidence;
- prove unbounded global strong-ring status;
- incrementally update a search after increasing the primitive-ring bound;
- compare results across different primitive cells without an explicit net map;
- certify the LTA tile set and multiplicity ratio; or
- compute tile geometry, cages, portals, or guest accessibility.

# Next stage

Stage 10C makes the primitive-ring bound an explicit rebuild boundary. Increasing
$K$ must reconstruct rings, ring indexes, induced symmetry, strength catalogs,
face candidates, compatibility systems, master refinements, Stage-10B searches,
and Stage-10A catalogs, then compare stable scientific keys and report every
change.

# References

1. V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M. Proserpio,
   *Three-Periodic Nets and Tilings: Natural Tilings for Nets*, Acta
   Crystallographica Section A **63**, 418--425 (2007), DOI:
   `10.1107/S0108767307038287`.
2. S. J. Chung, Th. Hahn, and W. E. Klee, *Nomenclature and Generation of
   Three-Periodic Nets: The Vector Method*, Acta Crystallographica Section A
   **40**, 42--50 (1984), DOI: `10.1107/S0108767384000088`.
