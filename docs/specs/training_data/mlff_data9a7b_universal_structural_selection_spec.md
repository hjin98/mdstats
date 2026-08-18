---
title: "MLFF-DATA9A7b Universal Structural Selection Providers"
version: "0.20.48a0"
date: "2026-07-30"
status: "implemented"
---

# Purpose

MLFF-DATA9A7b supplies a material-neutral structural feature path for MLFF data
preparation. It replaces the historical assumption that useful selection
features are necessarily LTA ring, cage, or site descriptors. The default
structural path now begins from local distances, smooth coordination, radial and
angular environment summaries, weighted connectivity, local packing, and
orientational order. Porous-material and zeolite semantics remain optional
extensions owned by later profile stages.

This stage does **not** move physical analysis algorithms into
`mdstats.training_data`. Numerical local-geometry kernels are owned by
`mdstats.analysis.local_structure`. The MLFF layer owns only:

- authorization of which DATA5 roles may be inspected;
- application of declared atom groups;
- aggregation into selection-grade frame vectors;
- immutable provider and policy lineage;
- generic structural-event records;
- integration with fitted feature metrics and selection queues.

# Scientific model

For atoms $i$ and $j$, define a chemistry-scaled normalized separation

$$
 x_{ij}=\frac{r_{ij}}{R_i+R_j},
$$

where $R_i$ and $R_j$ are declared covalent-radius values. The smooth
connectivity weight is

$$
 w_{ij}=\begin{cases}
 1, & x_{ij}\le x_\mathrm{on},\\
 \tfrac{1}{2}\left[1+\cos\!\left(\pi
 \frac{x_{ij}-x_\mathrm{on}}{x_\mathrm{off}-x_\mathrm{on}}\right)\right],
 & x_\mathrm{on}<x_{ij}<x_\mathrm{off},\\
 0, & x_{ij}\ge x_\mathrm{off}.
 \end{cases}
$$

This weight is a continuous local-connectivity measure. It is not a universal
chemical-bond assignment. The smooth coordination number is

$$
 C_i=\sum_{j\ne i}w_{ij}.
$$

The first implementation records the nearest-neighbor distance, weighted mean
and standard deviation of neighbor distance, smooth coordination, the count of
neighbors inside the numerical switching support, the $\ell_2$ norm of the
weighted degree, and neighbor-species entropy.

Radial environment features use Gaussian basis projections

$$
 G_{ik}=\sum_{j\ne i}
 \exp\!\left[-\frac{(r_{ij}-\mu_k)^2}{2\sigma_r^2}\right].
$$

A smooth local number-density proxy is

$$
 \rho_i^\mathrm{loc}=\frac{1}{4\pi R_\rho^3/3}
 \sum_{j\ne i}\exp\!\left[-(r_{ij}/R_\rho)^2\right].
$$

Angular moments are weighted averages of Legendre polynomials over unordered
neighbor pairs,

$$
 A_{i\ell}=\frac{\sum_{j<k}w_{ij}w_{ik}
 P_\ell(\hat{\mathbf r}_{ij}\!\cdot\!\hat{\mathbf r}_{ik})}
 {\sum_{j<k}w_{ij}w_{ik}}.
$$

Local bond-orientational order uses weighted spherical harmonics,

$$
 q_{\ell m}(i)=\frac{\sum_j w_{ij}Y_{\ell m}(\hat{\mathbf r}_{ij})}
 {\sum_jw_{ij}},\qquad
 q_\ell(i)=\left[\frac{4\pi}{2\ell+1}
 \sum_{m=-\ell}^{\ell}|q_{\ell m}(i)|^2\right]^{1/2}.
$$

The default policy records $q_4$ and $q_6$. These quantities depend on the
neighbor policy; therefore the complete numerical policy is immutable evidence.

# Analysis-owned API

`mdstats.analysis.local_structure` owns:

```python
LocalStructureFeaturePolicy
LocalStructureFeatureResult
compute_local_structure_features(...)
```

The implementation provides:

- triclinic minimum-image geometry;
- rigid-translation, rotation, and atom-permutation invariant scalar features;
- explicit missing masks when an angular statistic is undefined;
- finite-value guarantees;
- fallback-radius warning evidence;
- a declared dense-pair work budget.

The initial transparent kernel scales as $O(N_cN)$, where $N_c$ is the
number of selected center atoms and $N$ is the frame population. It fails
closed above `maximum_dense_pair_work`. A future analysis-owned optimization may
route the same public contract through the shared cell-list or Verlet backend.

# MLFF provider contracts

`mdstats.training_data.structural_selection` owns:

```python
StructuralFeatureProviderIdentity
UniversalStructuralSelectionPolicy
UniversalAtomicEnvironmentDescriptor
UniversalFrameStructuralDescriptor
GenericStructuralEventRecord
UniversalStructuralFeatureCatalog
StructuralSelectionProvider
UniversalStructuralSelectionProvider
build_universal_structural_feature_catalog(...)
```

A provider catalog binds:

- frame-catalog and DATA4 digests;
- optional material-profile and atom-group catalog digests;
- provider ID, provider version, and policy digest;
- per-atom environment descriptors;
- per-frame aggregated structural descriptors;
- generic geometry-only event records.

# Atom-group aggregation

The provider resolves the DATA9A7a atom-group catalog. Static selectors for all
atoms, atomic numbers, explicit indices, and composite set operations are
resolved internally. Metadata- or provider-generated groups require an explicit
`AtomGroupMembershipProvider`.

For each declared atom group and each element present in the authorized DATA6
role, the provider records selected statistics such as mean, standard deviation,
minimum, maximum, and selected quantiles. Empty groups are represented with
finite fill values plus explicit missing masks.

The element-column order is derived only from authorized structural-feature
frames. Sealed roles are not inspected merely to discover species or choose a
feature schema.

# Generic temporal events

For adjacent selected source frames within the declared maximum source gap, the
provider may record per-atom events for:

- smooth-coordination change;
- switching-support neighbor-count change;
- local-density change;
- orientational-order change;
- large minimum-image atomic displacement.

Thresholds are immutable policy values. These events are structural selection
evidence, not claims of chemical reaction, diffusion, or phase transition.
Those interpretations remain profile- or analysis-specific.

# DATA6 integration

DATA6 policy and bundle schemas advance to v2. New fields are:

```text
build_universal_structural_features
universal_structural_roles
universal_structural_features
```

When the caller omits `Data6Policy`, a DATA4 material-profile contract activates
the universal provider for the development role. LTA selection activates only
when DATA4 actually contains LTA partition features. Explicit policy remains
available for compatibility and controlled experiments.

Universal structural features may not materialize sealed or provenance-only roles, including locked-test, purged, or excluded roles. DATA6-v1 policy and bundle payloads remain readable and produce
an empty universal-provider catalog.

# DATA7 and selection integration

`FeatureMetricPolicyTemplate` accepts the optional block
`universal_structural`. The block consumes the immutable frame descriptors and
is fitted only within the declared final or fold-local training domain.

Species-environment selection now prefers the universal atomic descriptors and
performs deterministic farthest-point coverage separately for every present
species. It falls back to historical LTA atomic descriptors only when a
universal provider is absent. Generic structural events enter the rare-event
queue. Existing checkpoint-bound MACE descriptors remain the learned
representation path and complement, rather than duplicate, the interpretable
local geometry.

This stage intentionally does not yet generalize all Li/Na/K-specific objective
and difficulty summaries. Those migrate under DATA9A7c-DATA9A7d atom-group and
profile policies.

# Serialization and compatibility

All new records use canonical JSON-compatible payloads and content digests.
Feature ordering is explicit and must remain identical across a catalog.
Tampering, provider-policy mismatch, DATA4/frame lineage mismatch, and unknown
frame UIDs fail closed.

Compatibility requirements:

1. DATA4 v1 and v2 remain readable.
2. DATA6 v1 and v2 remain readable.
3. Existing LTA descriptors retain numerical behavior.
4. Model-free and MACE-backed DATA6 paths retain their prior contracts.
5. Generic execution must not import or serialize LTA semantics.

# Acceptance tests

The focused gate requires:

- rigid-motion and atom-permutation invariance;
- triclinic/periodic minimum-image behavior;
- smooth coordination across the switching interval;
- explicit missing masks for undefined angular moments;
- dense-pair complexity rejection;
- profile-driven DATA6 default activation;
- absence of LTA fields in generic catalogs;
- generic atom-group and per-element aggregation;
- generic temporal-event construction;
- immutable round trips and tamper rejection;
- DATA6-v1 read compatibility;
- sealed-role rejection;
- universal feature-metric fitting;
- generic per-species environment selection;
- unaffected legacy DATA6/DATA7/LTA regression tests.

# Deferred work

DATA9A7c adds phase- and geometry-specific activation policies. DATA9A7d moves
porous, zeolite, and LTA features fully behind optional extensions and removes
remaining hard-coded focus-species assumptions. DATA9A7e qualifies crystal,
amorphous, liquid, interface, and LTA workflows end to end.
