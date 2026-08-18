---
title: "Local Structure Feature Kernel Specification"
version: "0.20.48a0"
date: "2026-07-30"
status: "implemented"
owner: "mdstats.analysis.local_structure"
---

# Scope

This specification defines the analysis-owned per-atom local-structure feature
kernel introduced for MLFF-DATA9A7b. It owns geometry, normalization, numerical
policies, missing-value semantics, warnings, and complexity failure. It does not
own MLFF role authorization, atom-group aggregation, selection quotas, or
checkpoint decisions.

# API

```python
LocalStructureFeaturePolicy
LocalStructureFeatureResult
compute_local_structure_features(
    collection,
    *,
    frame_index,
    atom_indices=None,
    policy=None,
)
```

`atom_indices` selects center atoms. Every atom in the collection remains
eligible as a neighbor. The result contains one immutable row per selected
center, a stable feature-name order, a finite value matrix, an aligned missing
mask, warning codes, and policy metadata.

# Geometry

Coordinates use the collection cell and origin. Pair vectors use the shared
triclinic minimum-image geometry and the collection PBC flags. The output scalar
features must be invariant under:

- rigid translation;
- global rotation of positions and cell;
- atom permutation, after rows are mapped back to the same centers;
- equivalent periodic images.

Coincident distinct atoms produce warning evidence rather than silent division
by zero.

# Smooth connectivity

For pair radii $R_i+R_j$ and distance $r_{ij}$, define
$x_{ij}=r_{ij}/(R_i+R_j)$. A cosine switch is one below
`normalized_switch_start`, zero above `normalized_switch_end`, and continuous in
between. The feature kernel records:

- nearest-neighbor distance;
- weighted neighbor-distance mean and standard deviation;
- smooth coordination $\sum_jw_{ij}$;
- support-neighbor count for $w_{ij}>w_\mathrm{min}$;
- weighted-degree $\ell_2$ norm;
- neighbor-species entropy.

These are neighborhood descriptors, not a universal chemical-bond definition.
Fallback covalent radii are explicit policy and warning evidence.

# Radial, angular, orientational, and density features

The radial basis is a declared sequence of Gaussian centers and one width.
Angular features are weighted Legendre moments over unordered neighbor pairs.
Orientational features are weighted spherical-harmonic invariants $q_l$ for the
declared orders. The default records $q_4$ and $q_6$.

The local density is a Gaussian number-density proxy divided by the volume of a
sphere with the declared density scale. It is not a Voronoi volume and does not
claim free volume.

If fewer than two weighted neighbors exist, angular moments are zero-filled and
marked missing. If no weighted neighbor exists, all undefined weighted
statistics are similarly masked. Returned numerical arrays must remain finite.

# Complexity and backend

The initial implementation evaluates a dense center-by-population pair matrix.
Before allocation it evaluates

$$
W=N_\mathrm{centers}N_\mathrm{atoms}.
$$

If $W$ exceeds `maximum_dense_pair_work`, the function raises
`LocalStructureComplexityError`. No silent subsampling or policy relaxation is
allowed. A future cell-list or Verlet implementation may replace the kernel only
if it preserves the public feature contract and passes backend-equivalence tests.

# Ownership and use

The MLFF branch may:

- call this API on authorized frames;
- aggregate rows by immutable atom groups;
- use the resulting descriptors for fitted metrics and coverage selection;
- record generic structural changes.

The MLFF branch may not redefine the switching function, minimum-image
semantics, angular normalization, orientational normalization, or missing-value
rules.

The kernel is not automatically an `ObservableAnalysisCall`. Validation-grade
RDFs, coordination distributions, angle distributions, connectivity, and future
orientational-order distributions retain their own result schemas.

# Acceptance tests

Required tests include:

1. rigid translation and rotation invariance;
2. atom-permutation equivalence;
3. orthorhombic and triclinic periodic minimum images;
4. continuous coordination through the switching interval;
5. explicit angular missing masks;
6. finite orientational-order values;
7. selected-center behavior;
8. policy round trip and stable feature order;
9. coincident/fallback warnings;
10. fail-closed pair-work budget.
