---
title: "Coordinate Consumer Compatibility Adapters"
subtitle: "Stage C0B: exact migration of displacement, velocity, density, and plotting consumers"
date: "2026-07-24"
version: "0.19.96a0"
status: "implemented"
---

# Scope and ownership

Stage C0B migrates existing analysis and plotting consumers onto the Stage C0
coordinate foundation without defining a new estimator or changing the public
scientific meaning of established options. The owning module is
`mdstats.coordinates.consumer_adapters`.

The immutable `AtomisticFrameCollection` remains the physical source. C0A1 owns
source semantics and lattice-gauge validation. C0A2 owns affine registration.
C0B owns only the translation from legacy consumer options into those shared
contracts and any explicitly identified compatibility correction required to
reproduce the historical numerical result.

The migration boundary is:

$$
\begin{gathered}
\text{legacy option}
\longrightarrow
\text{C0 policy and source-bound registration}\\
\longrightarrow
\text{declared compatibility translation}
\longrightarrow
\text{consumer input}.
\end{gathered}
$$

Plotting, MSD, VACF, and density modules must not independently infer a
scientific drift frame after this stage.

# Persistent adapter products

## Consumer coordinate view

`ConsumerCoordinateView` stores:

- the authoritative `FrameRegistrationResult`;
- the selected source-frame indices;
- one explicit framewise translation correction;
- the exact consumer Cartesian positions;
- an optional display cell;
- the legacy spatial mode and translation convention;
- the reference-atom and weighting provenance;
- immutable metadata and a deterministic signature.

For selected frame $t$, the consumer coordinate is

$$
y_{i,t}=q_{i,t}+c_t,
$$

where $q_{i,t}$ is the C0A2 registered position and $c_t$ is a named
compatibility translation. Because $c_t$ is common to all atoms in one frame,

$$
y_{j,t}-y_{i,t}=q_{j,t}-q_{i,t}.
$$

The adapter therefore cannot silently alter same-frame pair geometry. Physical
bond, coordination, and topology calculations remain outside this plotting and
displacement compatibility view.

## Velocity translation view

`VelocityTranslationView` stores a translation policy, the drift-reference atom
set, the historical instantaneous drift velocity, its negative correction, and
a deterministic signature. It does not claim that the correction is the time
derivative of a fitted periodic position branch.

For weights $w_j$ over the declared reference set $R$,

$$
v_{\mathrm{drift},t}
=
\frac{\sum_{j\in R} w_j v_{j,t}}{\sum_{j\in R}w_j},
\qquad
v'_{i,t}=v_{i,t}-v_{\mathrm{drift},t}.
$$

This exactly preserves the pre-C0B VACF, velocity-spectrum, and velocity-derived
transport convention.

# Displacement compatibility

The accepted legacy modes remain:

- `coordinate_mode="laboratory"`: physical unwrapped Cartesian coordinates;
- `coordinate_mode="reference_cell"`: source fractional coordinates mapped to
  the resolved fixed reference cell;
- optional center-of-geometry or center-of-mass zero-centering.

For reference-cell mode,

$$
q_{i,t}=s_{i,t}H_{\mathrm{ref}}.
$$

When drift removal is requested,

$$
c_t=-\frac{\sum_{j\in R}w_jq_{j,t}}{\sum_{j\in R}w_j}.
$$

The resulting coordinates are regression-compatible with the historical D0
preparation layer. Existing MSD signatures remain estimator signatures; the C0B
registration signature is added as independent provenance.

# Plotting and density compatibility

The accepted spatial modes remain:

## Material

$$
y_{i,t}=s_{i,t}H_{\mathrm{display}}.
$$

Homogeneous cell deformation is removed by the fixed display-cell map. No
framework centroid correction is applied.

## Framework registered

Let $\bar s_{R,t}$ be the arithmetic mean of the already branch-consistent
framework fractional coordinates supplied by the plotting preparation path.
Then

$$
y_{i,t}
=
\left(s_{i,t}-\bar s_{R,t}+\bar s_{R,0}\right)
H_{\mathrm{display}}.
$$

This is the exact historical plotting convention. C0B owns the correction;
`framework_dynamics.py` no longer computes a scientific drift vector.

## Laboratory

$$
y_{i,t}=x_{i,t}.
$$

The optional display cell is a rendering coordinate only. Source lattice shifts
are transformed into that display basis without changing their physical
Cartesian vectors.

Atomic density, framework vertex density, framework edge density, trajectories,
and averaged framework geometry must all consume the same prepared view within
one scene. Density kernels and resource planning remain owned by their existing
density modules.

# Lattice-gauge compatibility envelope

New C0 APIs retain the conservative C0A1 continuity threshold. Historical MSD
and plotting paths admitted larger smooth variable-cell deformation. C0B may
retry a continuity failure with a data-derived envelope only when the observed
change is not a certifiable near-integer unimodular basis relabeling.

A detected unimodular relabeling remains fail-closed. Compatibility must not hide
a lattice-gauge discontinuity.

For partial periodicity, material plotting remains available through physical
registration plus the explicit display-cell map. A later density preflight may
still reject an operation whose scientific density contract requires full
periodicity. The adapter must not preempt that owning validation with a less
specific failure.

# Immutability and provenance

All stored arrays are finite, shape-validated, copied, and non-writeable.
Metadata is exposed as a read-only mapping. Registration round-trip validation
retains the C0A2 absolute tolerance for ordinary coordinates and adds an explicit
eight-ULP floor for historically admitted very large unwrapped absolute positions;
this changes only the numerical certification threshold, not the returned
coordinates. Signatures use canonical JSON plus array-byte SHA-256 digests and include:

- the underlying C0 registration or policy signature;
- selected frame and atom identities;
- compatibility translations or velocities;
- display-cell identity where applicable;
- legacy mode and weighting provenance; and
- migration metadata.

Consumer metadata must identify
`mdstats.coordinates.consumer_adapters` as the scientific drift owner and mark
`consumer_migration_stage="C0B"` where the owning result supports metadata.

# Failure behavior

The stage fails closed for:

- unsupported legacy modes;
- missing or invalid reference cells;
- invalid frame, atom, or reference selections;
- non-finite coordinates, cells, velocities, or weights;
- source/registration shape disagreement;
- a certifiable unapproved lattice-basis relabeling;
- a consumer position inconsistent with registration plus its declared
  correction;
- a nonzero velocity correction without a corresponding drift field; or
- signature inconsistency.

# Acceptance requirements

- laboratory and reference-cell displacement inputs match the pre-C0B oracle;
- center-of-geometry and center-of-mass displacement removal match the pre-C0B
  oracle;
- instantaneous VACF drift velocity is unchanged exactly;
- material, framework-registered, and laboratory plotting coordinates match the
  pre-C0B oracle;
- atomic and framework density consume the same source-bound scene registration;
- density values remain unchanged within a declared floating-point tolerance;
- pair geometry remains explicitly physical;
- plotting contains no independent scientific drift estimator;
- public legacy options remain accepted; and
- adjacent C0A1/C0A2/C0A3, displacement, velocity, density, and plotting tests
  remain green.

# Method provenance

Stage C0B introduces no borrowed numerical method. It delegates affine maps,
periodic closest-image decisions, and source-gauge validation to the separately
specified C0A1/C0A2 modules. Its package-specific contribution is the explicit,
source-bound compatibility boundary that preserves historical consumer outputs
while centralizing scientific coordinate ownership.
