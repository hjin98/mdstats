---
title: "Stage 11E8a-S4 Source-Bound Force-Density and Transition-Path Readiness"
version: "0.20.14a0"
date: "2026-07-26"
status: implemented baseline; revision-42 ENS/STAT migration planned
owner: "mdstats.analysis.density.pilot_force_paths"
---

# Purpose and boundary

## Revision-42 migration status

The current S4 runtime receives the legacy E0b PMF-force mask and fails closed
when it is empty. Revision 42 does not retroactively claim that ENS/STAT has been
implemented; it specifies that a future S4-compatible mask must come from an
exact `EvidenceAdmissibilityOverlay` bound to accepted production-regime and
ensemble-specific PMF certificates.

Stage 11E8a-S4 closes the list of *missing* Na-LTA NVE-continuation pilot evidence by
executing the existing Stage-11E3 force-refinement gate and by preparing the
Stage-11E6/11E6b transition-path boundary. It does not weaken the provenance or
state-validation requirements of those stages.

The implementation owner is:

```text
mdstats.analysis.density.pilot_force_paths
```

The source-bound entry point is:

```python
prepare_na_lta_300k_force_path_pilot(
    collection,
    trajectory_path,
    *,
    options=None,
    validated_frozen_catalog=None,
    ...,
)
```

The `300k` token is retained only in the legacy public function name for backward
compatibility. It is not an ensemble or temperature inference.

S4 consumes the S3 result and returns:

- the complete S3 pilot;
- one Stage-11E3 `ForceRefinementCatalog` on the central S2 spatial hypothesis;
- one signed `ForceDensityAgreementCertificate`;
- one signed `TransitionPathPreparationCertificate`;
- optional Stage-11E6 final segmentation and Stage-11E6b observed paths when
  every upstream gate is satisfied; and
- an updated fail-closed pilot dossier.

S4 does not infer a PMF, barrier, representative path, transition rate, Markov
model, or observed network.

# Force availability is not PMF admissibility

The real VASP trajectory contains physical per-atom forces. That fact alone does
not make the force samples admissible for the equilibrium identity

$$
\overline{\mathbf F}_q(\mathbf q)
\approx
k_\mathrm{B}T\,d_q\log p(\mathbf q).
$$

Stage 11E3 requires the intersection of:

- source-compatible registered positions;
- source-compatible transformed physical forces;
- represented-time support;
- an accepted production-regime certificate;
- tested stationarity under the Stage-11E-STAT contract; and
- an accepted ensemble-specific PMF-admissibility certificate.

S4 therefore keeps the following counts separate:

```text
joint_force_sample_count
pmf_force_sample_count
```

When physical joint samples exist but the PMF-force mask is empty, S4 executes
Stage 11E3 and records `pmf_provenance_rejected` for every retained attractor.
It does not silently promote a trajectory label, thermostat setting, or observed
temperature array into equilibrium PMF provenance.

# Force-density agreement certificate

The certificate is bound to the central S2 sample, density, attractor, and E3
signatures. It records:

- joint and PMF-admissible force-sample counts;
- supported density and matched-force node counts;
- supported-node fraction;
- local E3 refinement status counts;
- resolved-refinement fraction;
- absolute density-force residual norms where available;
- relative residuals normalized by

  $$
  \max(\lVert\overline{\mathbf F}_q\rVert,
       \lVert k_\mathrm{B}T d_q\log p\rVert,
       f_\mathrm{floor});
  $$

- cosine alignment where both vectors have nonzero norm; and
- whether the S2 scale and grid-topology hypothesis is authoritative.

The certificate status is one of:

```text
resolved
pmf_provenance_rejected
force_unavailable
insufficient_support
disagreement
spatial_hypothesis_unresolved
```

A locally passing force comparison remains
`spatial_hypothesis_unresolved` when the selected S2 spatial hypothesis is not
authoritative and the default S4 option requires that authority.

# Transition-path readiness

Stage 11E4 preliminary passages are not Stage-11E6b observed paths. S4 records
preliminary passage counts and outcomes, but it executes Stage 11E6 and 11E6b
only when both conditions hold:

1. the S2 spatial scale and grid-topology certificate are authoritative; and
2. a source-compatible Stage-11E5 validated frozen-state catalog is supplied.

If either condition fails, final segmentation and path reconstruction remain
`None`. A lightweight proxy or an unsigned list of attractors is not accepted as
a substitute for a validated state catalog.

The readiness status is one of:

```text
ready
executed_no_connections
missing_validated_states
spatial_hypothesis_unresolved
no_provisional_jumps
```

`no_provisional_jumps` is evidence of absent observed support in the represented
trajectory, not proof that transitions are impossible.

# Dossier semantics

S4 adds the last two required evidence records:

```text
force_density_agreement
transition_paths
```

After these records exist, `missing_required_evidence` is empty. The report is
`complete` only when all required records are resolved or not applicable.
Otherwise it is `scientifically_partial`; blocked force-density and path records
are listed explicitly in `blockers`.

This distinction is mandatory:

- missing evidence means the execution boundary was not run;
- blocked evidence means it was run and a declared scientific prerequisite
  failed;
- partial evidence means diagnostics exist but are insufficient for the final
  claim.

# Na-LTA NVE-continuation acceptance result

For the supplied 1,500-frame trajectory, the production ASE-backed replay
records:

- 1,440 represented-time joint position/force samples;
- zero PMF-admissible force samples;
- 24 local E3 refinements with `pmf_provenance_rejected`;
- eight S3 preliminary passages;
- five return excursions;
- three right-censored exits;
- zero preliminary inter-attractor jumps;
- no Stage-11E6 final segmentation; and
- no Stage-11E6b observed path catalog.

The dossier therefore advances from `blocked_missing_required_evidence` to
`scientifically_partial`. The force-density and transition-path records are
present but blocked for explicit scientific reasons.

# Determinism and failure rules

- S4 options and both certificates use canonical JSON SHA-256 signatures.
- Nested S1--S4 source, registration, sample, density, attractor, structural,
  temporal, force, segmentation, and path signatures are checked explicitly.
- Nonfinite metrics, invalid fractions, negative counters, source mismatches,
  or tampered signatures fail closed.
- Stage 11E6 is never executed before the spatial-authority and validated-state
  gates.
- Force data are never reclassified as PMF-admissible by S4.

# Required validation

Focused tests cover:

- signed options and certificate round trips;
- public root, analysis, and density exports;
- complete-force but PMF-inadmissible behavior;
- retention of all E2 attractors under E3 rejection;
- exact S3 temporal and structural binding;
- path-readiness refusal under unresolved S2 topology;
- empty `missing_required_evidence` with explicit blockers;
- adjacent Stage-11E3, E4, E6, E6b, S0--S3, VASP/ASE, API, and specification
  regressions; and
- full real-source replay.
