---
title: "Stage 7R Certification and Persistence Boundary Specification"
subtitle: "Scientific Results, Derived Indices, Search Workspaces, and Verification Certificates"
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

# Objective

Stage 7R consolidates the implemented topology, ring, symmetry, and strength
stack before Euclidean embedding. It enforces the architectural distinction

$$
\boxed{
\text{scientific result}
\neq
\text{derived index}
\neq
\text{search workspace}
\neq
\text{verification certificate}
}
$$

Runtime/API target:

```text
mdstats 0.19.19a0
```

No primitive-ring classification, periodic automorphism, symmetry-group order,
or bounded strength theorem is changed.

# Boundary table

| Category | Persistent? | Reconstructible? | Example |
|---|---:|---:|---|
| Scientific result | yes | not assumed | `PeriodicNetSymmetry`, `RingStrengthResult` |
| Derived index | optional | yes | `PrimitiveRingSymmetryIndex`, `PrimitiveRingIndex` |
| Search workspace | no | yes | `RingStrengthSearchWorkspace` |
| Positive certificate | yes | independently checkable | `RingStrengthWitness` |
| Negative bounded certificate | compact result + deterministic replay | yes | `STRONG_IN_DOMAIN` |

# Implemented refactors

## Core net symmetry

`PeriodicNetSymmetry` schema v3 stores only:

- source view/topology identities;
- normalized automorphism representatives;
- multiplication table;
- translation cocycle;
- inverse and identity indices;
- vertex orbits; and
- edge orbits.

It contains no primitive-ring keys, actions, or ring-search provenance.

## Primitive-ring symmetry index

`PrimitiveRingSymmetryIndex` binds one exact group to one exact ring catalog and
uses integer target positions in the action table. It records ring-catalog
completeness metadata and validates the induced action homomorphism.

## Strength result versus workspace

`RingStrengthResult` schema v2 stores:

```python
target_placement
domain
resources
status
diagnostics
candidate_set_digest
witness | None
```

It no longer stores every candidate placement. The deterministic transient
`RingStrengthSearchWorkspace` stores the exhaustive candidate tuple when a
caller explicitly asks for it.

For a candidate set $\mathcal P$, the persistent record stores

$$
d_{\mathcal P}
=
\operatorname{SHA256}
\left(\operatorname{canonical\_json}(\mathcal P)\right).
$$

## Independent strength verification

`RingStrengthResult.verify(index)` performs two checks:

1. for `WEAK_CERTIFIED`, recompute the physical lifted-edge parity of the target
   and witness components;
2. deterministically rebuild the declared finite domain, rerun the bounded
   cancellation solve, and require canonical result equality.

`from_dict(..., verify=True)` uses this path by default. Recomputing a payload
digest is therefore insufficient to forge a scientific certificate.

## GF(2) memory policy

The finite cancellation backend now declares conservative capacities:

```python
FiniteRingCancellationResources(
    max_matrix_bits,
    max_provenance_bits,
)
```

For $N$ candidates and $E$ physical edge basis elements, the preflight estimates

$$
B_{\text{matrix}}=NE,
\qquad
B_{\text{provenance}}=N\min(N,E).
$$

Exceeding either bound raises a resource error. The strength layer translates it
to `UNRESOLVED_TRUNCATED`; it never reports a false negative strength result.

## Shared barycentric placement

The exact rational equilibrium solve is extracted to
`PeriodicBarycentricPlacement`. Symmetry discovery consumes that source-bound
object instead of carrying an anonymous private coordinate tuple.

## Fast view lookup

`PeriodicNetView` constructs transient immutable maps

```text
atom index -> vertex position
FrameworkEdgeKey -> edge position
```

so repeated automorphism and ring-action lookups are $O(1)$ rather than linear
searches.

# Schema changes

| Object | Previous | Current |
|---|---|---|
| `PeriodicNetSymmetry` | v2 | v3 |
| `PeriodicNetSymmetryDiscovery` | v1 | v2 |
| `RingStrengthResult` | v1 | v2 |
| `RingStrengthCatalog` | v1 | v2 |
| `PrimitiveRingSymmetryIndex` | absent | v1 |
| `PeriodicBarycentricPlacement` | absent | v1 |

These are intentional alpha API changes. Legacy payloads are not silently
upgraded because their ownership boundaries are ambiguous.

# Measured Na-LTA effect

For the 96-operation Na-LTA symmetry and 82 primitive rings:

```text
core PeriodicNetSymmetry JSON       ~0.83 MB
PrimitiveRingSymmetryIndex JSON     ~1.01 MB
combined discovery JSON             ~1.84 MB
```

The former combined ring-heavy symmetry payload was approximately 9.17 MB.

For one depth-eight 8-ring strength calculation with 3,240 candidate placements:

```text
persistent RingStrengthResult JSON  ~4 KB
candidate workspace                 transient/reconstructible
```

The earlier persistent result scaled approximately linearly with every complete
candidate key and placement.

# Deferred work

Stage 7R deliberately does not implement:

- symmetry-orbit-level strength transport;
- a sparse or two-pass GF(2) solver;
- a compact standalone negative row-space certificate;
- a Euclidean invariant Gram matrix;
- automatic disk/face construction; or
- natural tiling.

The symmetry-equivariant strength layer remains required before final face
selection, but it does not block Stage 8A embedding.

# Acceptance gate

The consolidation passes when:

1. core symmetry round trips without ring data;
2. ring action round trips only with the exact group and ring catalog;
3. strength payloads contain no candidate workspace;
4. forged weak witnesses fail independent verification;
5. GF(2) memory limits return unresolved status;
6. direct barycentric placement and discovery produce identical exact
   coordinates and symmetry groups;
7. all prior Stage-4--7 scientific regressions pass; and
8. package-wide tests reveal no import or schema regressions.
