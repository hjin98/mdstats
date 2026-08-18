---
title: "Affine Frame Registration and Coordinate Products"
subtitle: "Stage C0A2: physical, translation-registered, and reference-material views"
date: "2026-07-24"
version: "0.19.93a0"
status: "implemented"
---

# Scope and dependencies

Stage C0A2 consumes the source-field and periodic lattice-gauge contract from C0A1. It
constructs analysis-specific affine maps but does not migrate MSD, VACF, density, plotting,
or structural consumers; that work belongs to C0B and C0A3.

The package uses row vectors. For frame $t$,

$$
q_{i,t}=x_{i,t}M_t+b_t,\qquad G_t=H_tM_t,
$$

where $H_t$ is the C0A1 gauge-reconciled source cell.

# Policies

## Physical

$$
M_t=I,\qquad b_t=0,\qquad G_t=H_t.
$$

## Translation registered

$$
M_t=I,\qquad b_t=-\tau_t,\qquad G_t=H_t.
$$

## Reference material

For a full-rank, fully periodic reference cell $H_{\rm ref}$,

$$
M_t=H_t^{-1}H_{\rm ref},\qquad G_t=H_{\rm ref}.
$$

The policy may be composed with the same matched-reference translation gauge. Reference
material registration preserves material/fractional internal motion; it is not a physical
bond-length coordinate system.

# Persistent reference and translation gauge

A reference set is a deterministic tuple of atom indices with center-of-geometry,
center-of-mass, or explicit positive weights. Reference coordinates are taken from one
declared source frame after lattice-gauge reconciliation and mapped into each frame's
pre-translation registered cell.

For residuals $d_{j,t}=\widetilde q_{j,t}-q_{j,\rm ref,t}$, solve on the registered torus

$$
\tau_t=\arg\min_{\tau}\sum_jw_j
\|\operatorname{MIC}_{G_t,R}(d_{j,t}-\tau)\|_R^2.
$$

The implementation forms deterministic candidates by repeatedly lifting all residuals
around a seed, taking their weighted mean, and resolving each lift with the certified
closest-image solver. Candidate minima are reduced modulo the lattice and deduplicated.
The selected result records weighted RMS, maximum residual, competing-minimum separation,
closest-image ambiguity, convergence, and reference provenance. This matched-displacement
solver is package-specific; it is not a wrapped-coordinate center average.

# Temporal translation-branch lift

The torus representative obeys

$$
\tau_t^{\rm lift}=\tau_t+n_tG_t,
\qquad n_t\in\mathbb Z^3.
$$

For a trajectory, each continuous segment chooses the current lattice branch closest to
the previous lifted translation under the fit metric. Declared segment starts reset the
lift. A closest-image tie fails closed. Independent ensembles receive torus representatives
only and do not acquire invented temporal continuity.

# Coordinate products

Every result exposes:

- `registered_unwrapped_cartesian`;
- `registered_wrapped_fractional`;
- `registered_image_shifts`;
- `registered_cells`;
- framewise $M_t$, torus translation, and lifted translation.

They obey

$$
q=(s+k)G,
$$

where $s$ is wrapped fractional position and $k$ is the integer image shift. Position
round trips, affine inverse round trips, and cell identities are validated before success.

# Displacements and forces

Same-frame displacement transforms as

$$
\Delta q=\Delta xM_t.
$$

For an externally defined affine map, force is a covector:

$$
F_q=F_xM_t^{-\mathsf T}.
$$

The implementation verifies numerical work invariance. A matched translation fitted from
the same atoms is not promoted automatically to an exact generalized force. Exact
translation-relative force status requires an explicitly declared target set disjoint from
the reference set; otherwise the result is diagnostic while the independent PMF
admissibility status from C0A1 is retained.

# Failure behavior

The stage fails closed for:

- a source contract not bound to the collection;
- missing reference cell for `reference_material`;
- partial periodicity for matched torus translation or reference-material mapping;
- singular/incompatible affine maps;
- invalid atom indices or nonpositive weights;
- nonconstant reference set;
- unresolved closest-image or branch-lift ties;
- fixed-domain requests whose registered cells are not constant within tolerance;
- coordinate, cell, or force-work validation failures.

# Acceptance requirements

- $G_t=H_tM_t$ for every frame;
- reference-material mapping yields the declared fixed cell;
- a common framework translation is removed across a periodic boundary;
- branch lifting preserves continuous unwrapped trajectories and respects reset boundaries;
- wrapped coordinates and image shifts exactly reconstruct unwrapped registered positions;
- affine forward/inverse round trips pass;
- covector-transformed forces preserve $F\cdot\Delta x$;
- C0A1 unimodular basis reconciliation does not change registered physical positions;
- deterministic serialization preserves signatures.
