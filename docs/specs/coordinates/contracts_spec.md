---
title: "mdstats source-coordinate contract specification"
subtitle: "Stage C0A1: normalized field semantics, force provenance, and reference-cell definitions"
author: "mdstats"
date: "2026-07-24"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.85in
fontsize: 10pt
---

# Scope

`mdstats.coordinates.contracts` owns the source meanings that must be known before
an analysis-specific spatial registration is constructed. It does not transform
positions, velocities, forces, cells, rings, tiles, or cages. Those operations
begin in Stage C0A2.

The module makes four distinctions explicit:

1. normalized positions are cell-origin-relative Cartesian coordinates obtained
   from the stored unwrapped fractional coordinates and the reported row-vector
   cell;
2. velocities may be native Cartesian values, finite-difference values, absent,
   or semantically unknown;
3. forces are Cartesian covector components only when the normalized source frame
   is known; and
4. geometric force transformation and PMF-force admissibility are independent
   claims.

Unknown semantics fail only the claims that require them. A collection with
unknown velocity semantics may still support position density, pair geometry,
and other position-only analyses.

# Source-field semantics

`SourceFieldSemantics` stores:

```text
position_frame
velocity_frame
force_frame
box_origin_frame
```

The initial normalized position contract is

```text
cell_origin_relative_cartesian
```

because source Cartesian coordinates are converted through

$$
\mathbf f=(\mathbf x-\mathbf o)H^{-1},
\qquad
\mathbf x_{\mathrm{normalized}}=\mathbf fH,
$$

where $\mathbf o$ is the source box origin and $H$ is the row-vector cell.
The source origin remains separately available in `AtomisticFrameCollection.origins`.

Velocity semantics distinguish native normalized Cartesian values from velocities
reconstructed by finite differences. Both are geometrically transformable in a
later exact policy only when that policy supplies the required time derivatives.
They are not statistically equivalent for high-frequency dynamics.

Force semantics are

```text
normalized_cartesian_covector
unavailable
unknown
```

The covector label is mandatory because under a row-vector affine position map

$$
\mathbf q=\mathbf xM+\mathbf b,
$$

work invariance requires

$$
\mathbf F_q=\mathbf F_xM^{-\mathsf T}.
$$

# Source metadata and backward compatibility

Newly normalized collections record a canonical
`metadata["source_field_semantics"]` mapping. Older collections without this
mapping are resolved from the normalized collection and its
`FrameCollectionProvenance`.

Converting a trajectory subset to an independent ensemble sets the stored
velocity-frame status to `unavailable`, matching the existing rule that ensemble
outputs discard velocities.

# Force provenance and admissibility

`ForceSourceProvenance` records three independent source facts:

```text
physical_force_complete
bias_or_constraint_force
stochastic_or_thermostat_force
```

Each fact is `present`, `absent`, or `unknown`. Unknown is not interpreted as
absent.

`ForceAdmissibilityContract` then reports two independent statuses.

## Geometric status

For the C0A1 source identity map, a complete force field with known Cartesian
covector semantics is

```text
exact_external_affine_covector
```

An absent or semantically unknown force is

```text
generalized_force_unavailable
```

The translation-relative and structure-fitted statuses are reserved for later
registration policies.

## PMF-force status

A source force is `pmf_force_admissible` only when all of the following are
explicitly established:

- the physical force is complete;
- no untracked bias or constraint force is present; and
- no stochastic or thermostat-force contribution contaminates the stored force.

If contamination is present, the result is
`pmf_force_inadmissible_untracked_bias_or_constraint`. If any required provenance
is unknown, the result is `pmf_force_provenance_unknown`.

Geometric exactness never upgrades PMF admissibility.

# Reference-cell definition

`ReferenceCellDefinition` supports only the two Stage-C0 initial sources:

```text
explicit_matrix
selected_source_frame
```

An explicit matrix is caller supplied. A selected-source-frame definition uses
one cell after the periodic lattice gauge has been validated and, where enabled,
reconciled.

The initial reference-material scope requires:

- a finite full-rank $3\times3$ row-vector cell;
- full periodicity on all three axes;
- source/reference handedness agreement; and
- an immutable digest containing the matrix, source kind, selected frame,
  periodic axes, tolerance, and lattice-gauge signature.

Partial periodicity is rejected only when a reference-material cell is requested.
Position-only physical or translation-only analyses may continue to use collections
whose own analysis contract supports partial periodicity.

# Deterministic persistence

The following schemas are authoritative:

```text
mdstats.source-field-semantics.v1
mdstats.force-admissibility.v1
mdstats.reference-cell-definition.v1
mdstats.source-coordinate-contract.v1
```

Digests use canonical JSON with sorted keys, compact separators, finite numeric
values, and SHA-256. Arrays are serialized as row-major nested lists.

# Validation

Focused validation must cover:

- normalized semantic inference;
- explicit metadata replay;
- velocity-only claim rejection without blocking position claims;
- geometric-force availability with PMF provenance unknown;
- clean, biased, and missing force provenance;
- explicit and selected-frame reference cells;
- full-rank/full-periodic enforcement;
- handedness mismatch rejection; and
- deterministic contract signatures.
