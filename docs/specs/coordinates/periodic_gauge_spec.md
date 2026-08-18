---
title: "mdstats periodic lattice-gauge specification"
subtitle: "Stage C0A1: cell identity, basis continuity, and explicit unimodular reconciliation"
author: "mdstats"
date: "2026-07-24"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.85in
fontsize: 10pt
---

# Scope

`mdstats.coordinates.periodic_gauge` validates the identity of the reported
periodic lattice basis before Stage C0A2 interprets frame-to-frame cell changes as
physical affine deformation. It does not construct the affine registration map.

The controlling failure rule is:

$$
\boxed{\text{a basis relabeling is never silently interpreted as strain}}
$$

# Row-vector lattice convention

Cells follow the package convention

$$
\mathbf x=\mathbf fH.
$$

Two reported cells can describe the same lattice under an integer basis change

$$
H'=UH,
\qquad U\in GL(3,\mathbb Z),
\qquad |\det U|=1.
$$

For each frame, the gauge stores an integer matrix $Q_t$ such that

$$
\widetilde H_t=Q_tH_t
$$

is the gauged cell used by downstream registration. Without reconciliation,
$Q_t=I$ for every accepted frame.

# Validation order

For every source cell, the implementation checks:

1. finite $3\times3$ shape;
2. determinant magnitude above the configured singularity tolerance;
3. condition number below the configured limit;
4. handedness and periodic-axis compatibility; and
5. basis/deformation continuity.

`AtomisticFrameCollection` already stores one immutable three-axis PBC vector, so
periodic-axis continuity is guaranteed by normalized collection construction and
is recorded in the gauge signature. A future source model with frame-dependent
PBC must pass an explicit continuity audit before entering this module.

# Trajectory and ensemble comparison policies

Time-ordered trajectories compare frame $t$ with the gauged frame $t-1$.
Independent ensembles compare every frame with gauged frame zero. The ensemble
policy avoids inventing a temporal order.

The direct reported-basis change is

$$
r_{\mathrm{direct}}
=
\frac{\lVert H_t-\widetilde H_{\mathrm{cmp}}\rVert_F}
     {\max(\lVert\widetilde H_{\mathrm{cmp}}\rVert_F,\epsilon)}.
$$

If this value is below the continuity tolerance, the reported basis is retained.

# Candidate unimodular reconciliation

When the direct change is too large, form

$$
A_t=\widetilde H_{\mathrm{cmp}}H_t^{-1}
$$

and round it to the nearest integer matrix $Q_t$. The candidate is accepted
only when:

- $|\det Q_t|=1$;
- the normalized distance from $A_t$ to $Q_t$ is below
  `integer_matrix_tolerance`;
- the gauged cell $Q_tH_t$ is continuous with the comparison cell; and
- the gauged residual is below the stricter reconciliation residual tolerance.

The integer tolerance is intentionally larger than floating-point roundoff because
small physical strain can accompany a discrete basis relabeling. The independent
gauged-cell residual prevents an arbitrary affine change from being accepted only
because its inverse happens to lie near an integer matrix.

If a valid nontrivial candidate is found while reconciliation is disabled, the
module raises `UnsupportedBasisChangeError`. When reconciliation is enabled, the
matrix is applied explicitly and retained in provenance.

A determinant-sign change may be reconciled only through a certified
orientation-reversing unimodular matrix. Otherwise it raises
`CellHandednessError`.

# Unresolved changes

If neither the reported basis nor a certified unimodular gauge provides a
continuous cell identity, the module raises `LatticeBasisContinuityError`.
The first implementation does not guess whether the discontinuity is a restart,
large physical deformation, malformed cell, or unsupported basis operation.
Callers must segment the trajectory or provide a later explicit policy.

# Persistent records

`PeriodicLatticeGauge` retains:

```text
source digest
frame semantics
periodic axes
common gauged handedness
per-frame comparison frame
reported and gauged cells
integer gauge matrix
reported determinant and condition number
direct and gauged relative changes
integer-candidate residual
frame status
options and immutable signature
```

Per-frame statuses are:

```text
reference
continuous_reported_basis
reconciled_unimodular_basis
```

The source digest binds frame IDs, PBC, cells, origins, and frame semantics. A
selected-source-frame reference cell must carry the lattice-gauge signature.

# Initial limitations

Stage C0A1 deliberately does not:

- optimize over a broad family of integer matrices;
- reconcile non-unimodular supercell changes;
- infer atom remapping after a supercell transformation;
- accept abrupt unresolved deformation as physical by default;
- segment restarts automatically; or
- construct registered coordinates.

These boundaries keep the first gauge deterministic and fail closed.

# Validation

Focused tests must include:

- smooth physical cell changes;
- exact and strained unimodular shear relabelings;
- orientation-reversing unimodular relabeling;
- default rejection when reconciliation is disabled;
- explicit reconciliation with the expected inverse matrix;
- unresolved noninteger cell jumps;
- handedness changes without lattice equivalence;
- trajectory versus ensemble comparison anchors; and
- deterministic gauge signatures.
