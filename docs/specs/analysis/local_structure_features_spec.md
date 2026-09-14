---
title: "Local Structure Feature Kernel Specification"
version: "0.20.48a0"
date: "2026-07-30"
status: "implemented"
owner: "mdstats.analysis.local_structure"
reconciled_date: "2026-09-14"
reconciled_against_commit: "e8d04144f55c72d799ffcd3fe40c75e47078a66d"
reconciliation_semantics: "documentation-only numerical-contract completion; no feature-value method change"
---

# Scope

This specification defines the analysis-owned per-atom local-structure feature
kernel introduced for MLFF-DATA9A7b. It owns geometry, normalization, numerical
feature definitions, missing-value semantics, warnings, and complexity failure.
It does not own MLFF role authorization, atom-group aggregation, target-order
metric fitting, selection quotas, or checkpoint decisions.

The equations below make the already implemented numerical contract
reconstructible without reverse-engineering `mdstats.analysis.local_structure`.
They are a documentation reconciliation of the existing feature-value method,
not a change to that method.

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
center, a stable feature-name order, a finite binary64 value matrix, an aligned
missing mask, warning codes, and policy metadata.

# Geometry and pair domain

Coordinates use the collection cell and origin. Pair vectors use the shared
triclinic minimum-image geometry and the collection periodic-boundary-condition
(PBC) flags. The center atom is excluded from its own neighbor population.
Distinct atoms at minimum-image distance less than or equal to
`coincident_tolerance_angstrom` produce warning evidence. They remain valid for
scalar distance, connectivity, radial, density, and species-mixing features, but
are excluded from angular/orientational unit-vector features so division by a
near-zero norm cannot occur.

The output scalar features must be invariant under:

- rigid translation;
- global rotation of positions and cell;
- atom permutation, after rows are mapped back to the same centers; and
- equivalent periodic images.

# Covalent radii and smooth connectivity

For center `i` and distinct neighbor `j`, let `r_ij` be the minimum-image
Cartesian distance. Let `R_i` and `R_j` be ASE covalent radii. If an atomic
number has no finite positive ASE radius, use
`fallback_covalent_radius_angstrom` and emit the corresponding fallback warning.
Define

$$
x_{ij}=\frac{r_{ij}}{R_i+R_j}.
$$

With `a = normalized_switch_start` and `b = normalized_switch_end`, the exact
smooth connectivity weight is

$$
w_{ij}=\begin{cases}
1, & x_{ij}\le a,\\
\frac12\left[1+\cos\left(\pi\frac{x_{ij}-a}{b-a}\right)\right],
& a<x_{ij}<b,\\
0, & x_{ij}\ge b.
\end{cases}
$$

Let

$$
W_i=\sum_j w_{ij}.
$$

The scalar connectivity/distance features are:

$$
d_i^{\min}=\min_j r_{ij},
$$

$$
\mu_{r,i}=\frac{\sum_j w_{ij}r_{ij}}{W_i},
$$

$$
\sigma_{r,i}=\sqrt{\frac{\sum_j w_{ij}(r_{ij}-\mu_{r,i})^2}{W_i}},
$$

$$
C_i=\sum_j w_{ij},
$$

$$
H_i=\#\{j:w_{ij}>w_{\min}\},
$$

and

$$
D_i=\sqrt{\sum_j w_{ij}^2},
$$

where `w_min = minimum_weight`.

If there is no distinct neighbor, `nearest_neighbor_distance_angstrom` is
zero-filled and marked missing. If `W_i=0`, the weighted mean and weighted
standard deviation are zero-filled and marked missing. `smooth_coordination`,
`hard_neighbor_count`, and `weighted_degree_l2` remain defined as zero in that
case.

These descriptors express smooth local support; they are not a universal
chemical-bond definition.

# Neighbor-species entropy

For species `s`, define its smooth neighbor mass

$$
W_{i,s}=\sum_{j:Z_j=s}w_{ij}
$$

and, when `W_i>0`,

$$
p_{i,s}=\frac{W_{i,s}}{W_i}.
$$

The species-mixing feature is

$$
S_i=-\sum_{s:p_{i,s}>0}p_{i,s}\log p_{i,s}.
$$

If `W_i=0`, the stored value is zero and the feature is marked missing.

# Local density and radial environment

Let `R_d = density_radius_angstrom`. The local number-density proxy is

$$
\rho_i=
\frac{\sum_j\exp[-(r_{ij}/R_d)^2]}
{\frac43\pi R_d^3}.
$$

It is a Gaussian number-density proxy, not a Voronoi volume and not a claim of
free volume.

For every configured radial center `c` and
`\sigma_r = radial_width_angstrom`, define

$$
G_i(c)=\sum_j
\exp\left[-\frac12\left(\frac{r_{ij}-c}{\sigma_r}\right)^2\right].
$$

The radial coordinates are emitted in strictly increasing configured center
order as `radial_density_r{center:.3f}_angstrom`.

Neither the density nor radial Gaussian uses the smooth connectivity weight;
the minimum-image distance itself controls these kernels.

# Angular Legendre moments

Angular/orientational neighbors are those satisfying both

$$
w_{ij}>w_{\min}
$$

and

$$
r_{ij}>r_{\mathrm{coincident}},
$$

where `r_coincident = coincident_tolerance_angstrom`. For such a neighbor let

$$
\hat{\mathbf r}_{ij}=\frac{\mathbf r_{ij}}{r_{ij}}.
$$

For every configured Legendre order `l`, define the unordered-pair weight sum

$$
W_i^{(2)}=\sum_{j<k}w_{ij}w_{ik}.
$$

When at least two angular neighbors exist and `W_i^(2)>0`, the angular moment is

$$
A_{i,l}=
\frac{\sum_{j<k}w_{ij}w_{ik}
P_l(\hat{\mathbf r}_{ij}\cdot\hat{\mathbf r}_{ik})}
{W_i^{(2)}},
$$

where `P_l` is the Legendre polynomial of degree `l`. Otherwise the stored value
is zero and the angular coordinate is marked missing.

# Bond-orientational order

For every configured orientational order `l`, the weighted Steinhardt
bond-orientational invariant is defined by the spherical-harmonic addition
theorem. With the angular-neighbor set above and

$$
W_i^{(1)}=\sum_j w_{ij},
$$

$$
q_{i,l}^2=
\frac{
\sum_j w_{ij}^2
+2\sum_{j<k}w_{ij}w_{ik}
P_l(\hat{\mathbf r}_{ij}\cdot\hat{\mathbf r}_{ik})
}
{(W_i^{(1)})^2},
$$

and

$$
q_{i,l}=\sqrt{\max(0,q_{i,l}^2)}.
$$

This is equivalent to the conventional weighted spherical-harmonic definition

$$
q_l=\sqrt{\frac{4\pi}{2l+1}\sum_{m=-l}^{l}|q_{lm}|^2}.
$$

If no angular/orientational neighbor remains, the stored value is zero and the
coordinate is marked missing. One valid neighbor is sufficient to define the
orientational invariant; the two-neighbor requirement applies to the unordered
pair angular moment, not to `q_l`.

# Feature order and default numerical policy

The stable feature order is:

1. `nearest_neighbor_distance_angstrom`;
2. `weighted_neighbor_distance_mean_angstrom`;
3. `weighted_neighbor_distance_std_angstrom`;
4. `smooth_coordination`;
5. `hard_neighbor_count`;
6. `weighted_degree_l2`;
7. `neighbor_species_entropy`;
8. `local_number_density_angstrom^-3`;
9. radial coordinates in configured center order;
10. `angular_legendre_l{order}` in increasing configured order; and
11. `bond_orientational_q{order}` in increasing configured order.

The current default policy is:

```text
normalized_switch_start = 1.15
normalized_switch_end = 1.75
radial_centers_angstrom = (1.0,1.5,2.0,2.5,3.0,3.5,4.0,5.0)
radial_width_angstrom = 0.35
density_radius_angstrom = 4.0
angular_legendre_orders = (1,2,3,4)
orientational_orders = (4,6)
minimum_weight = 1e-8
coincident_tolerance_angstrom = 1e-8
fallback_covalent_radius_angstrom = 1.0
maximum_dense_pair_work = 4_000_000
policy_version = mdstats.analysis.local-structure.2026-07.v1
```

Policy values must be finite and positive where applicable; switch start must be
less than switch end; radial centers are strictly increasing; and
`minimum_weight < 1`.

# Missing values and finite representation

Every returned numerical array is finite. Undefined coordinates are represented
by value zero plus an aligned `missing_mask=true`; zero is therefore not by
itself evidence that a quantity was observed. Current missing rules are:

- no distinct neighbor -> nearest-neighbor distance missing;
- zero smooth weight sum -> weighted distance mean/std and species entropy
  missing;
- fewer than two valid angular neighbors or zero angular pair-weight sum -> each
  angular Legendre moment missing;
- no valid orientational neighbor -> each bond-orientational invariant missing.

Other coordinates remain defined by the formulas above, including zero-valued
coordination/count/degree, radial, and density results.

# Precision and backend equivalence

Geometry and feature arrays are evaluated and returned in IEEE-754 binary64
under the current implementation. The mathematical formulas, feature order,
missing-mask semantics, and policy values above are normative; a particular
NumPy/SciPy reduction kernel, vectorization strategy, fused/non-fused execution
choice, or loop decomposition is not independently promoted to analysis
semantic identity unless an accepted numerical owner explicitly does so.

A replacement backend must preserve the public feature contract and pass
backend-equivalence evidence appropriate to its consumers. A consumer whose
later discrete decision can change under provider roundoff must additionally
bind the provider policy/version and satisfy that consumer's precision/
discrete-decision equivalence contract rather than assuming arbitrary backend
roundoff is harmless.

# Complexity and backend

The current implementation evaluates a dense center-by-population pair matrix.
Before allocation it evaluates

$$
W=N_\mathrm{centers}N_\mathrm{atoms}.
$$

If `W` exceeds `maximum_dense_pair_work`, the function raises
`LocalStructureComplexityError`. No silent subsampling or policy relaxation is
allowed. A future cell-list or Verlet implementation may replace the kernel only
if it preserves the feature contract above and passes backend-equivalence tests.

# Ownership and use

The MLFF branch may:

- call this API on authorized frames;
- aggregate rows by immutable atom groups or by an independently defined neutral
  element view;
- use the resulting descriptors for fitted metrics and coverage selection; and
- record generic structural changes.

The MLFF branch may not redefine the switching function, minimum-image
semantics, radial/density kernels, angular normalization, orientational
normalization, or missing-value rules.

The kernel is not automatically an `ObservableAnalysisCall`. Validation-grade
radial distribution functions (RDFs), coordination distributions, angle
distributions, connectivity, and future orientational-order distributions retain
their own result schemas.

# Acceptance tests

Required tests include:

1. rigid translation and rotation invariance;
2. atom-permutation equivalence;
3. orthorhombic and triclinic periodic minimum images;
4. exact switch fixtures below, inside, and above the transition interval;
5. direct scalar references for weighted mean/std, coordination, hard-neighbor
   count, weighted degree, and species entropy;
6. direct scalar references for radial and local-density Gaussian kernels;
7. direct scalar Legendre-moment and bond-orientational fixtures, including the
   one-neighbor orientational case;
8. explicit angular/orientational missing masks;
9. selected-center behavior;
10. policy round trip and stable feature order;
11. coincident/fallback warnings; and
12. fail-closed pair-work budget.
