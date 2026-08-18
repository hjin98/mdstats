> Superseded by `ld8_ld9_architecture_revision_audit.md`; retained as the audit of the initial LD8 draft.

# LD8 finite-support refinement documentation audit

Date: 2026-07-21
Package baseline: `mdstats 0.19.53a0`
Scope: architecture documentation only; no implementation code changed

## Updated artifact

- `docs/arch_manuals/mdstats_dynamical_framework_density_architecture_standard.md`
- `docs/arch_manuals/mdstats_dynamical_framework_density_architecture_standard.pdf`

## Normative decisions recorded

- Retain `kernel_tail_tolerance=1.0e-8`.
- Preserve the normalized `discrete_periodized_v1` CIC-plus-Gaussian estimator.
- Keep the single-level logical grid and default `16 x 16 x 16` block shape.
- Add LD8 as an approved, unimplemented execution-refinement stage.
- Replace fine-node pair-stream support discovery with a reusable periodic block-support atlas.
- Deposit one global sparse CIC source field per requested scientific field.
- Use exact block-local direct convolution as the first target implementation.
- Reuse support metadata for integration, HDR ordering, contour support, and connected components.
- Retain LD7 and LD1-A as migration and numerical oracles.
- Keep multilevel AMR, variable bandwidth, and a looser Gaussian cutoff unauthorized.

## Validation performed

- Markdown converted successfully with Pandoc and XeLaTeX.
- PDF preflight reports 48 letter-sized pages, embedded fonts, outline entries, and no encryption.
- All 48 pages rendered successfully at 120 dpi.
- Pages containing the LD8 plan and revision record were visually inspected; no clipping, overlap, missing glyphs, or broken equations were observed.

## Next authorized work

1. LD8-S0 - support contract and immutable records.
2. LD8-S1 - exact periodic atlas construction and Phase-B planning.

Implementation and focused tests are intentionally deferred until explicit approval.
