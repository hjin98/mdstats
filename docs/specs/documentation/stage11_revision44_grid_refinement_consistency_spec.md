---
title: "Stage 11 Revision-44 Grid-Refinement and Density-Ownership Consistency Specification"
version: "0.20.16a0"
date: "2026-07-27"
---

# Purpose

This specification owns the revision-44 documentation contract for partial reuse
of the tested atomic-density numerical-resolution machinery. It does not modify
runtime density values or the current Stage 11E8a dossier.

# Required decisions

- The architectural choice is a partial refactor, not wholesale reuse and not
  idea-only duplication.
- Atomic-density code is the regression oracle for common grid geometry,
  periodic spread, reciprocal resolution, artificial broadening, budgeted grid
  planning, and dense/local-sparse feasibility.
- Common backend-neutral machinery moves toward `mdstats.analysis.density` under
  GR0/GR1 and remains available through plotting compatibility adapters.
- Plotting retains adaptive visual bandwidth/grid coupling and one-grid visual
  acceptance.
- Stage 11 scientific refinement holds the kernel covariance fixed throughout a
  deterministic grid ladder.
- Field resolution, basin convergence, and transition-corridor convergence use
  separate certificates.
- A budget-limited ladder that does not converge remains
  `unresolved_due_to_resolution_budget`.
- Grid convergence never substitutes for SAMP1/SAMP2 sampling confidence.
- GR4 prevents held-out blocks from selecting bandwidth, grid, or candidate
  complexity.
- GR5 closes D0b-D0d only after dense, sparse, scientific, visual, and public-API
  regressions pass.

# Required records

```text
CommonDensityGridPolicy
ScientificGridRefinementPolicy
DensityFieldResolutionCertificate
BasinGridConvergenceCertificate
CorridorGridConvergenceCertificate
```

# Acceptance

The normative manual must contain architecture revision 44, stages 11E-GR0
through 11E-GR5, the fixed-kernel equation, separate field/basin/corridor
certificates, the budget-limited unresolved rule, the plotting-versus-scientific
policy separation, and the cross-fitted numerical-hypothesis freeze.

The scientific density index must link the permanent grid-refinement
specification. Existing revision-43 trajectory-quality and earlier architecture
contracts remain in force.
