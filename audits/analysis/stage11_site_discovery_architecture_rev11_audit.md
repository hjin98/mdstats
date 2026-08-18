# Stage 11 data-driven site-discovery architecture revision 11 audit

Date: 2026-07-24

## Scope

Planning-only revision of `docs/arch_manuals/stage11_site_kinetics_architecture.md`.
Production source and test files are unchanged from architecture revision 10.

## Corrections applied

- Split species-independent structural ring geometry from species-dependent ion coordination.
- Replaced one unconstrained harmonic fit with complementary cyclic-index and rank-safe actual-angle contracts.
- Added even-ring Nyquist handling, fit rank/condition diagnostics, explicit weighting, normalization, phase gauge, and undefined-phase semantics.
- Added registered structural geometry views reconstructed from transformed atoms.
- Made direct local displacement and exact ordered M-O/M-T distances authoritative; residual harmonics are diagnostic only.
- Added structural multi-association, geometry-forward coordination checks, and occupancy-conditioned fingerprint diagnostics.
- Added Stage 11E5a and corrected the persistent-data and validation contracts.

## Document validation

- Markdown converted with Pandoc/XeLaTeX.
- PDF preflight passed: 39 pages, openable, unencrypted, text based.
- All pages rendered after final conversion.
- Selected pages covering the revised harmonic, registration, stage-sequence, validation, and references sections were visually inspected with no clipping or overlap.

## Code boundary

No implementation or test claim is made. Stage C0 remains the next implementation stage.
