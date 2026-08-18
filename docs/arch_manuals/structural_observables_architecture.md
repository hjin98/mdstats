---
title: "Structural Observables Architecture Manual"
subtitle: "RDF, Coordination, Neighbor Angles, Atomic Connectivity, and General Structural Validation"
author: "mdstats project"
date: "2026-07-30 (revision 2 - universal local-structure kernel implemented)"
geometry: margin=0.82in
toc: true
toc-depth: 3
numbersections: true
fontsize: 10.5pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{longtable}
  - |-
    \usepackage{microtype}
  - |-
    \usepackage{xurl}
---

# Purpose and status

This manual owns the general static structural observables in
`mdstats.analysis`. It covers pair radial distributions, coordination states,
neighbor-angle distributions, and atomic connectivity. These observables are
usable for crystalline solids, amorphous solids, liquids, surfaces, and
interfaces when their selections and neighbor definitions are scientifically
appropriate.

The following public implementations are complete and regression-tested:

- `compute_pair_rdf` and `RDFResult` feature helpers;
- `compute_coordination_distribution`;
- `compute_bond_angle_distribution`;
- `compute_atomic_connectivity` with distance, hysteretic, reference, and
  explicit definitions;
- catalog-derived atomic connectivity statistics in
  `mdstats.analysis.topology_statistics`;
- `compute_local_structure_features` with chemistry-scaled smooth
  connectivity, radial projections, angular moments, local-density proxy, and
  local $q_4/q_6$ orientational order for selection-grade use.

The DATA9A7b focused gate adds analytic, invariance, periodicity,
missing-value, and complexity-budget tests for the local-structure kernel. The
standardized observable-call facade remains separate; the local selection
kernel is not automatically registered as a physical-validation observable.

# Phase-aware MLFF consumption

MLFF-DATA9A7c may choose which selection-grade local-structure feature families
are exposed for a declared phase or geometry. That policy filtering does not
change ownership: `mdstats.analysis.local_structure` calculates the complete
numerical local environment under an explicit policy, while the MLFF branch
selects and aggregates authorized columns for dataset coverage. Phase profiles
must not redefine RDF, coordination-distribution, angle-distribution, topology,
or physical validation semantics.

# Ownership boundary

The analysis modules own:

1. mathematical definitions and normalization;
2. periodic geometry and neighbor semantics;
3. result dataclasses and scientific metadata;
4. warnings, failure modes, and numerical validation;
5. module-specific plotting and export where already implemented.

The MLFF branch may select, parameterize, invoke, pair, and record these
analyses. It must not duplicate their algorithms, reinterpret their arrays, or
claim that a call alone constitutes scientific acceptance.

The stable bridge is analysis-owned:

```python
from mdstats.analysis import (
    ObservableAnalysisCall,
    ObservableAnalysisRecipe,
    execute_observable_recipe,
)
```

`mdstats.training_data` owns only paired reference/MLFF orchestration through
`MLFFObservableValidationPlan` and `run_mlff_observable_validation`.

# Shared neighbor and geometry contract

RDF, coordination, angle, and connectivity results depend on a declared
neighborhood policy. The policy is part of the scientific observable and must
not be treated as a plotting option.

The underlying periodic neighbor subsystem owns:

- exact triclinic minimum-image geometry;
- strict cutoff semantics;
- dense, cell-list, and Verlet-cache execution;
- deterministic CSR neighbor results;
- deformation-aware candidate reuse where explicitly enabled;
- backend diagnostics without changing accepted physical pairs.

The controlling architecture is
`periodic_neighbor_search_architecture.{md,pdf}`.

# Selection-grade local-structure kernel

`mdstats.analysis.local_structure` owns a reusable per-atom structural feature
kernel. It was introduced for MLFF data selection, but its geometry and
normalization remain analysis responsibilities so that other branches may reuse
it without importing `mdstats.training_data`.

For pair separation $r_{ij}$, a continuous weight is generated from the
normalized distance $r_{ij}/(R_i+R_j)$ using a cosine switching interval. The
resulting weighted degree is a smooth coordination proxy. The kernel also
returns nearest-neighbor and weighted-distance summaries, Gaussian radial
projections, a Gaussian local-density proxy, weighted neighbor-species entropy,
Legendre angular moments, and weighted spherical-harmonic $q_4$ and $q_6$.

The result is invariant to rigid translation, global rotation, and atom ordering.
Undefined angular moments use an explicit missing mask rather than a fabricated
number. The complete radius, switching, radial-basis, angular-order, and work
budget policy is serialized with the result lineage.

This first implementation is intentionally transparent and dense. It fails
closed when $N_cN$ exceeds the declared pair-work budget. A later optimization
may use the periodic cell-list or Verlet backend while retaining the same public
contract.

These features are not, by themselves, validation-grade RDFs, angle
distributions, integer coordination states, or phase classifiers. The MLFF
branch may aggregate them for selection, but interpretation remains outside the
kernel.

# Pair radial distribution

`compute_pair_rdf` owns partial pair histograms, shell-volume normalization,
and cumulative coordination. `RDFResult` additionally owns auditable smoothing,
first-peak, first-minimum, and first-shell coordination helpers.

RDF is suitable for broad structural comparison, but it is not a complete local
environment representation. Similar RDFs can hide different angular,
connectivity, or medium-range structures.

# Coordination distributions

`compute_coordination_distribution` returns the authoritative integer
per-center, per-frame coordination matrix together with distributions and
summary statistics. The cutoff may be explicit, supplied by a pair-cutoff
registry, or derived from a compatible RDF minimum.

A coordination cutoff is a model definition. For liquids and thermally active
systems, users should consider sensitivity to the cutoff and use hysteresis or
smooth coordination in future extensions when state switching is the target.

# Neighbor-angle distributions

`compute_bond_angle_distribution` computes species-resolved `A-B-C` neighbor
angles, supports coordination filters, and exposes angle-, center-, and
frame-weighted statistics. The term *neighbor angle* is preferred unless a
chemical bond definition has been established independently.

# Atomic connectivity

`compute_atomic_connectivity` owns discrete weighted-by-definition graph states
for fixed-population frame collections. Supported policies include:

- instantaneous strict-distance connectivity;
- two-threshold hysteretic trajectory connectivity;
- reference-state discovery/formation/retention connectivity;
- externally supplied explicit connectivity.

Connectivity is not universal chemical bonding. Its definition, scope, pair
cutoffs, frame ordering, and persistence policy are mandatory provenance.

The topology-statistics branch, not the MLFF branch, owns graph-state occupancy,
degree and pair distributions, contact persistence, transitions, and residence
statistics.

# Standardized observable calls

`mdstats.analysis.observable_validation` provides a registry and immutable
JSON-safe recipes. It delegates to the owner function and preserves native
result objects.

Implemented structural call IDs are:

| Observable ID | Owner |
|---|---|
| `structure.rdf` | `mdstats.analysis.rdf.compute_pair_rdf` |
| `structure.coordination` | `mdstats.analysis.coordination.compute_coordination_distribution` |
| `structure.bond_angle` | `mdstats.analysis.bond_angle.compute_bond_angle_distribution` |
| `topology.atomic_connectivity` | `mdstats.analysis.atomic_connectivity.compute_atomic_connectivity` |
| `topology.atomic_statistics` | `mdstats.analysis.topology_statistics.compute_atomic_connectivity_statistics` |

The facade may decode simple serialized pair-cutoff registries and distance,
hysteretic, or reference connectivity definitions. More specialized framework
and ring calls remain direct APIs owned by their manuals.

# Physical validation role

For MLFF validation, these analyses are usually run on matched reference and
model-generated configurations or trajectories. The call parameters must match:

- atom/species/group selection;
- thermodynamic condition;
- cell and periodicity semantics;
- frame window and stride;
- neighbor and cutoff definition;
- averaging and normalization.

Comparison metrics and acceptance tolerances are separate policy. For example,
an RDF comparison may use pointwise differences, integrated absolute error,
peak displacement, or shell-coordination differences. This manual does not
choose one universal tolerance.

# Missing general structural observables

The following additions are recommended, but are not implemented in this
package revision:

## Static structure factor

Add total and partial `S(q)` from positions or from compatible RDFs, including
finite-cell and scattering-weight provenance. This is the highest-priority
missing general validation observable for liquids and amorphous solids.

## Bond-orientational order

A selection-grade local $q_4/q_6$ implementation now exists in
`local_structure`. A full validation observable is still missing: it should add
local and global distributions, neighbor-averaged variants, explicit phase
classification policies, uncertainty summaries, and standardized observable
call/result schemas. These are useful for crystallinity, freezing, polymorph
discrimination, and amorphous local order.

## Local volume and packing

The local-structure kernel includes a Gaussian number-density proxy, but it does
not provide geometric local volume or free volume. Add Voronoi or another
declared local-volume estimator, local composition, packing anisotropy, and
free-volume summaries. Robust periodic triclinic support and degeneracy handling
are required before release.

## Crystalline local classifiers

Polyhedral-template matching, adaptive common-neighbor analysis, local lattice
orientation, and local elastic strain should form an optional crystalline
subbranch. They must not become universal defaults.

## Dihedral and molecular internal coordinates

Add generic dihedral distributions and reusable molecule/group definitions for
molecular liquids, polymers, and flexible adsorbates.

## Interface profiles

Add analysis-owned one-dimensional number-density, mass-density, composition,
orientation, and stress profiles along a user-declared interface coordinate.
The interface normal and region assignment must be explicit inputs.

# Porous and framework-specific extension

Primitive rings, ring centers, windows, cages, natural tilings, and site
semantics are not owned here. They are optional structural extensions governed
by:

- `framework_ring_architecture.{md,pdf}`;
- `topology_statistics_architecture.{md,pdf}`;
- `stage11_site_kinetics_architecture.{md,pdf}`.

An MLFF material profile may append those calls when the system has a meaningful
porous or framework topology. Generic material profiles must not activate them.

# Testing and acceptance

Every new structural observable requires:

1. analytic or exactly enumerable synthetic tests;
2. triclinic and periodic-boundary tests;
3. selection and empty-data failure tests;
4. backend-equivalence tests where neighbor search is used;
5. immutable result and provenance tests;
6. at least one physically interpretable domain fixture;
7. a separate module specification before MLFF exposes it through the call
   registry.

## Thermomechanical and energetic boundary

This manual does not own equation-of-state fitting, elastic constants,
thermodynamic fluctuation response, stress-correlation viscosity, harmonic
phonons, surface/interface energies, defect energetics, or migration barriers.
Those analyses are defined in
`thermomechanical_energetic_validation_architecture.{md,pdf}`. Structural
observables may be used as diagnostics for those workflows, but their numerical
definitions and result schemas remain here.
