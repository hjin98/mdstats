# Stage 11 architecture revision 14 audit

Date: 2026-07-24

## Scope

Planning-only update to `mdstats 0.19.91a0`. No production Python or test behavior is changed.

## Closed issues

1. Framework translation is now a periodic matched-displacement gauge with branch and residual diagnostics.
2. KDE covariance is separated from the analysis geometry metric used by closest images, gradient flow, ridges, basins, and correspondence.
3. Triclinic MIC is a certified closest-lattice-vector problem rather than componentwise fractional rounding.
4. Multiscale attractor lineages now yield an explicit scale-consensus catalog or a retained ambiguous hypothesis set.
5. Scientific topology is limited to a supported periodic cell complex; unknown cells cannot create basins or saddles.
6. Single-attractor components have explicit supported-boundary or probability-content core fallbacks without invented barriers.
7. Local harmonic force fits contain an intercept and can estimate a force-defined center with uncertainty and chart-containment checks.
8. Structural forward checks convert registered centers back to physical framewise coordinates before M-O distances are evaluated.
9. Biased density and biased force evidence have separate admissibility semantics.
10. Geometry-conditioned refinement is frozen and one-pass by default; iterative reassignment requires a separate versioned algorithm.
11. HDBSCAN and k-means comparisons use periodic geometry rather than ordinary wrapped Euclidean distance.

## Consistency checks

- Row-vector affine and force-center formulas are internally consistent.
- Differential topology is defined in a metric-orthonormal chart.
- Unsupported, supported-background, transition, basin, and unresolved cell states are distinct.
- Stage C0A2, E0b, E1, E2, E3, E5a, and E5b deliverables reflect the new contracts.
- The persistent data model includes the translation gauge, analysis metric, supported complex, scale decision, and force-fit provenance.
- The next implementation stage remains Stage C0A1, followed by C0A2.

## Artifact validation

- Main manual: 51 pages.
- PDF preflight: passed; openable, unencrypted, text-based.
- All 51 pages rendered successfully and the revised registration, metric, multiscale, support, force, forward-model, dynamic-refinement, persistent-data, stage-plan, and test sections were visually inspected.
- Markdown fences and display-math delimiters are balanced.
- All 35 cited Stage 11 references are defined and used; no undefined citation identifiers remain.
- Production `mdstats/` and `tests/` trees are byte-identical to revision 13.
- Package ZIP integrity and SHA-256 are checked after archive creation.
