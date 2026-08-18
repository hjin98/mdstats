---
title: "Natural-Tiling Candidate and Properness Certification Specification"
subtitle: "Stage 10A: Exact Scientific Symmetry Action, Multidimensional Eligibility, and Ambiguity Preservation"
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

Stage 10A certifies whether a caller-proposed Stage-9 periodic cell complex is an
eligible **natural-tiling candidate** under the currently available finite
scientific evidence. It also proves or disproves properness relative to the full
exact automorphism group of one immutable `PeriodicNetView`.

Runtime/API target:

```text
mdstats 0.19.24a0
```

The stage introduces four persistent result layers:

```text
PeriodicCellComplexSymmetryAction
NaturalTilingCertification
NaturalTilingCandidate
NaturalTilingCatalog
```

Stage 10A does **not** discover natural face sets, propagate local face sectors,
split provisional tiles along non-face strong rings, resolve published crossing
alternatives, refine the primitive-ring bound, or run the LTA end-to-end natural-
tiling search. Those responsibilities remain Stages 10B--10D.

The first backend is therefore a certifier, not a tiling generator:

```text
caller-proposed Stage-9 complex
        + complete exact net symmetry
        + bounded strength evidence
        + face/witness compatibility
        + exact partition certificate
        -> Stage-10A candidate certification
```

# Scientific definitions

## Natural-tiling candidate

A candidate is one scientific translation-labelled periodic cell complex whose
selected face rings, tile attaching maps, and partition evidence satisfy the
active Stage-10A gates. Candidate identity is the identity of the scientific
complex, not the identity of any auxiliary triangulation or tetrahedral mesh.

## Properness

Let $G_{\mathrm{view}}$ be the exact periodic net fixed by the selected
`PeriodicNetView`, and let $\mathcal T$ be the proposed periodic cell complex.
The target condition is

$$
\operatorname{Aut}(\mathcal T)
=
\operatorname{Aut}(G_{\mathrm{view}}).
$$

The tiling uses the net as its fixed $1$-skeleton. Every automorphism of the
tiling therefore restricts to an automorphism of that net:

$$
\operatorname{Aut}(\mathcal T)
\subseteq
\operatorname{Aut}(G_{\mathrm{view}}).
$$

Stage 10A proves equality by checking the reverse inclusion: every representative
of the complete exact net automorphism group must preserve all scientific face
orbits and tile attaching maps modulo lattice translation and orientation.

This properness condition follows the natural-tiling framework of Blatov,
Delgado-Friedrichs, O'Keeffe, and Proserpio [1]. The exact translation-labelled
cell action and its finite group-composition verification are mdstats-specific
constructions built on the periodic vector representation [2] and the exact
periodic-net symmetry layer [3].

# Source contract

The high-level certifier consumes mutually consistent instances of:

```python
certify_natural_tiling_candidate(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    ring_index: PrimitiveRingIndex,
    strength_catalog: RingStrengthCatalog | None,
    face_certificates: Sequence[FacePlacementCertificate],
    selected_witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem | None,
    complex_: PeriodicCellComplex,
    partition_certificate: PeriodicPartitionCertificate | None,
    *,
    symmetry_resources: NaturalTilingSymmetryResources | None = None,
) -> NaturalTilingCandidate
```

The first backend requires:

- a Stage-7R `PeriodicNetSymmetryDiscovery`, not an arbitrary user-supplied
  subgroup;
- a source-bound `PrimitiveRingSymmetryIndex` inside that discovery result;
- one scientific face-orbit representative per primitive-ring key;
- face certificates and selected witnesses aligned with every Stage-9 face;
- exact view, topology, embedding, ring-catalog, complex, partition, and
  compatibility source identity; and
- a Stage-9 complex that has already passed its chain, shell, and quotient
  invariants.

An absent strength catalog, compatibility system, or partition certificate does
not cause a false negative. It produces an explicit unresolved certification
dimension.

# Exact scientific symmetry action

## Oriented cell image

The image of an oriented quotient face or tile is represented by

```python
OrientedCellImage(
    target_cell_index: int,
    image_shift: tuple[int, int, int],
    orientation: Literal[-1, 1],
)
```

For a source cell representative $c$, the record means

$$
g(c,\mathbf 0)
=
s\,(c',\boldsymbol\delta),
\qquad s\in\{-1,+1\}.
$$

A translated occurrence obeys

$$
g(c,\mathbf n)
=
s\,(c',A_g\mathbf n+\boldsymbol\delta),
$$

where $A_g\in\mathrm{GL}(3,\mathbb Z)$ is the lattice matrix of the normalized
periodic automorphism.

## Face action

Each scientific face is an oriented `FacePlacement`. The existing exact ring
action maps its primitive-ring placement and cyclic parameterization. The face
orientation changes by the orientation of that parameterization.

For source face $f_i$ and chosen target representative $f_j$,

$$
g f_i
=
s_{g,i}\,t_{\boldsymbol\delta_{g,i}} f_j.
$$

The first backend requires one selected face orbit per ring key. If a mapped ring
key is absent from the selected face set, the operation is certified as not
preserving the proposed tiling.

Auxiliary `FaceEmbeddingWitness` triangulations do not participate in this action.
A symmetry-related face may be certified by a different admissible mesh witness
without changing the scientific tiling.

## Tile attaching-map action

A tile shell is an integer face chain

$$
\partial_3 T_a
=
\sum_k c_k(f_{i_k},\mathbf n_k),
\qquad c_k\in\{-1,+1\}.
$$

Applying $g$ gives

$$
g(\partial_3T_a)
=
\sum_k
c_k s_{g,i_k}
\left(
 f_{j_k},
 A_g\mathbf n_k+\boldsymbol\delta_{g,i_k}
\right).
$$

The resulting exact chain must equal a translated, optionally orientation-reversed
target shell:

$$
g(\partial_3T_a)
=
s_{g,a}\,t_{\boldsymbol\eta_{g,a}}\partial_3T_b.
$$

No geometric centroid, floating tolerance, auxiliary tetrahedron, or tile label is
used. `PeriodicTileShell.label` remains non-authoritative metadata; scientific
tile identity is determined by its translation-labelled attaching map.

## Complete finite group-action check

Normalized periodic automorphism representatives compose up to one common lattice
translation. Let

$$
g_o g_i
=t_{\mathbf c(o,i)}g_d,
$$

where $g_d$ is the stored normalized representative and
$\mathbf c(o,i)$ is `composition_translation_table[o][i]`. For every face and
tile image, Stage 10A verifies

$$
\boldsymbol\delta_d
=
A_o\boldsymbol\delta_i
+
\boldsymbol\delta_o
-
\mathbf c(o,i),
$$

with target indices and orientation signs composed exactly. Failure is an
internal invariant error, not an unresolved scientific result.

# Public symmetry API

```python
@dataclass(frozen=True)
class NaturalTilingSymmetryResources:
    max_operation_face_images: int = ...
    max_operation_tile_images: int = ...
    max_composition_checks: int = ...
```

All limits are preflighted transactionally.

```python
build_periodic_cell_complex_symmetry_action(
    complex_: PeriodicCellComplex,
    symmetry: PeriodicNetSymmetry,
    ring_symmetry: PrimitiveRingSymmetryIndex,
    *,
    resources: NaturalTilingSymmetryResources | None = None,
) -> PeriodicCellComplexSymmetryAction
```

The result stores one dense operation record per exact group representative:

```python
CellComplexSymmetryOperation(
    operation_index: int,
    status: PRESERVED | NOT_PRESERVED,
    face_images: tuple[OrientedCellImage, ...],
    tile_images: tuple[OrientedCellImage, ...],
    reason: str | None,
)
```

A missing exact face or tile image is a proof of non-invariance. It is not a
resource-truncation state. Resource exhaustion raises
`NaturalTilingResourceError` before publishing a partial action.

# Multidimensional certification

## Independent state enum

```python
CertificationState = CERTIFIED | REJECTED | UNRESOLVED
```

The persistent certification record is

```python
NaturalTilingCertification(
    primitive_ring_bound: int,
    primitive_complete: CertificationState,
    symmetry_complete: CertificationState,
    strength_complete: CertificationState,
    embedding_complete: CertificationState,
    compatibility_complete: CertificationState,
    cell_complex_valid: CertificationState,
    partition_certified: CertificationState,
    properness: PropernessStatus,
    resource_truncations: tuple[str, ...],
    unresolved_assumptions: tuple[str, ...],
    rejection_reasons: tuple[str, ...],
)
```

The dimensions have the following meaning.

| Dimension | `CERTIFIED` condition | `REJECTED` condition | `UNRESOLVED` examples |
|---|---|---|---|
| primitive | lower-closed primitive catalog, no truncation, complete through every selected face size | reserved | incomplete bound or source truncation |
| symmetry | complete Stage-7R discovery and source-bound ring action | reserved | unsupported future discovery domain |
| strength | every selected face is `STRONG_IN_DOMAIN` in its declared finite domain | at least one selected face is `WEAK_CERTIFIED` | missing result, truncated domain, incomplete source |
| embedding | every selected face has the chosen certified admissible disk witness | reserved | missing or non-admissible witness |
| compatibility | selected witness tuple violates no finite constraint and retains no unresolved constraint | selected tuple activates a hard forbidden constraint | absent system or active unresolved constraint |
| cell complex | Stage-9 scientific object exists and validates | reserved | future conditional complex backend |
| partition | exact Stage-9 certificate belongs to this complex | reserved | certificate absent |

`STRONG_IN_DOMAIN` remains explicitly bounded. Stage 10A does not promote it to
an unbounded global strong-ring theorem.

## Properness state

```python
PropernessStatus =
    CERTIFIED_PROPER
  | CERTIFIED_IMPROPER
  | UNRESOLVED
```

For the current first backend:

- a complete discovery plus a preserved scientific action gives
  `CERTIFIED_PROPER`;
- a complete discovery plus any non-preserving operation gives
  `CERTIFIED_IMPROPER`; and
- future unsupported or incomplete symmetry backends must use `UNRESOLVED`.

## Aggregate eligibility

```python
CandidateEligibility = ELIGIBLE | INELIGIBLE | UNRESOLVED
```

The aggregation rule is deterministic:

1. Any rejected dimension, certified improperness, or rejection reason gives
   `INELIGIBLE`.
2. All dimensions certified, properness certified, and no unresolved/truncation
   record gives `ELIGIBLE`.
3. Every other combination gives `UNRESOLVED`.

The aggregate never replaces the independent dimensions.

# Candidate identity and evidence identity

```python
NaturalTilingCandidate(
    periodic_net_view_digest: str,
    topology_graph_digest: str,
    primitive_ring_catalog_digest: str,
    periodic_cell_complex_digest: str,
    selected_ring_keys: tuple[PrimitiveRingKey, ...],
    certification: NaturalTilingCertification,
    symmetry_action_digest: str | None,
    partition_certificate_digest: str | None,
    strength_catalog_digest: str | None,
    compatibility_system_digest: str | None,
    digest: str,
    evidence_digest: str,
)
```

Two digests are intentional.

- `digest` is the scientific candidate identity. It depends on the immutable
  source identities, the Stage-9 complex, and the selected ring keys.
- `evidence_digest` includes certification states and evidence digests.

Thus two different exact tetrahedralizations or admissible face meshes can
certify the same scientific tiling without creating duplicate candidates.

# Catalog and ambiguity

```python
NaturalTilingOutcomeKind = NONE | UNIQUE | MULTIPLE
```

```python
NaturalTilingCatalog(
    periodic_net_view_digest: str,
    primitive_ring_catalog_digest: str,
    candidates: tuple[NaturalTilingCandidate, ...],
    outcome: NaturalTilingOutcome,
    essential_ring_keys: tuple[PrimitiveRingKey, ...],
)
```

Only `ELIGIBLE` candidates contribute to the outcome:

$$
N_{\mathrm{eligible}}=0\Rightarrow\texttt{NONE},
$$

$$
N_{\mathrm{eligible}}=1\Rightarrow\texttt{UNIQUE},
$$

$$
N_{\mathrm{eligible}}>1\Rightarrow\texttt{MULTIPLE}.
$$

Unresolved candidates remain stored even when the eligible outcome is `NONE`.
Enumeration order is never a scientific tie-breaker. Duplicate scientific
digests are collapsed deterministically; conflicting eligible and rejected
evidence for one scientific identity is rejected as inconsistent input.

An empty catalog is permitted when the caller supplies the view and ring-catalog
digests explicitly.

# Essential rings

A primitive-ring orbit is called essential only when it is used as a face by an
eligible candidate. The catalog stores the union

$$
\mathcal R_{\mathrm{essential}}
=
\bigcup_{\mathcal T\in\mathcal C_{\mathrm{eligible}}}
\mathcal R_{\mathrm{face}}(\mathcal T).
$$

Unresolved or rejected candidates do not create essential rings.

# Persistence and replay

Canonical schemas:

```text
mdstats.cell-complex-symmetry-action.v1
mdstats.natural-tiling-candidate.v1
mdstats.natural-tiling-catalog.v1
```

All records use canonical JSON and SHA-256 digests.

- `PeriodicCellComplexSymmetryAction.from_dict(...)` rebuilds the exact action
  from the supplied complex, symmetry, and ring-symmetry sources and rejects any
  altered image table.
- Candidate and catalog deserialization revalidates canonical identity,
  evidence, multiplicity, and essential-ring invariants.
- Dense local indices remain bound to source digests.

# Resource and failure policy

The scientific result is never partially published after a resource failure.

| Condition | Result |
|---|---|
| face/tile image preflight exceeds declared limit | raise `NaturalTilingResourceError` |
| group-composition preflight exceeds declared limit | raise `NaturalTilingResourceError` |
| exact mapped face absent | operation `NOT_PRESERVED` |
| exact mapped tile shell absent | operation `NOT_PRESERVED` |
| ambiguous duplicate target tile orbit | raise `NaturalTilingInputError` |
| altered serialized action | raise `NaturalTilingSerializationError` |
| missing optional strength/compatibility/partition evidence | candidate `UNRESOLVED` |
| certified weak face or certified improper symmetry | candidate `INELIGIBLE` |

# Validation fixtures

The focused first-backend fixture is the simple-cubic net with one vertex orbit,
three translation-labelled edge orbits, three square primitive-ring face orbits,
and one cubic tile orbit. Exact symmetry discovery produces 48 normalized
operations.

The Stage-10A gate verifies:

- 48 preserved scientific operation records;
- three face images and one tile image per operation;
- orientation-reversing tile images where required;
- exactly
  $48^2(3+1)=9216$ face/tile group-composition checks;
- independence from auxiliary tetrahedral mesh identity;
- explicit non-preservation when a scientific image is absent;
- transactional resource failure;
- eligible/proper/unique certification;
- unresolved missing compatibility or partition evidence;
- rejection of a certified weak selected face;
- scientific deduplication across auxiliary evidence;
- explicit multiple eligible identities;
- empty `NONE` catalogs;
- serialization replay; and
- digest/tamper rejection.

# Explicit non-responsibilities

Stage 10A does not:

- enumerate face selections;
- infer tile shells from local face sectors;
- split cells along admissible non-face strong rings;
- implement crossing-ring alternatives;
- prove global unbounded ring strength;
- perform primitive-bound refinement and downstream rebuild;
- certify the LTA $[4^6]$, $[4^6.6^8]$, and
  $[4^{12}.6^8.8^6]$ tile set;
- compute tile geometry, cages, or portals; or
- require auxiliary meshes to be symmetric as combinatorial triangulations.

# References

1. V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M. Proserpio,
   *Three-Periodic Nets and Tilings: Natural Tilings for Nets*, Acta
   Crystallographica Section A **63**, 418--425 (2007), DOI:
   `10.1107/S0108767307038287`.
2. S. J. Chung, Th. Hahn, and W. E. Klee, *Nomenclature and Generation of
   Three-Periodic Nets: The Vector Method*, Acta Crystallographica Section A
   **40**, 42--50 (1984), DOI: `10.1107/S0108767384000088`.
3. O. Delgado-Friedrichs and M. O'Keeffe, *Identification of and Symmetry
   Computation for Crystal Nets*, Acta Crystallographica Section A **59**,
   351--360 (2003), DOI: `10.1107/S0108767303012017`.
