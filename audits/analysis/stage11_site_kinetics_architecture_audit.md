# Stage 11 Site-Discovery Architecture Revision 15 Audit

## Scope

This is a planning-only revision of `mdstats 0.19.91a0`. Production Python code and tests are unchanged.

## Corrected contracts

Revision 15 closes the final issues found in the revision-14 audit:

- framework translation uses a dedicated `RegistrationFitMetric`, not the downstream basin/topology metric;
- periodic translation has a segment-continuous `TranslationBranchLift` with integer branches, reset points, continuity residuals, and fail-closed ambiguity;
- the log-density `DensityScoreCovector` is distinct from the `MetricGradientVector`; equilibrium force is compared only with the covector in the same coordinate measure;
- discovery, model selection, final validation, and optional all-data refit are separate through `SelectionValidationProtocol`;
- moving geometry-conditioned regions use an exclusive `AssignmentConflictStatus`, cannot double-count occupancy, and report lower/upper occupancy bounds under unresolved overlap;
- independent-run transition paths are pooled by `RegistrationCompatibilityClass`, not by identical member registration signatures;
- optional PMF reconstruction distinguishes full-torus Hodge structure from integrability on sampled subdomains with boundaries, holes, and independent circulation generators.

The persistent-data model, implementation stages, acceptance gates, and adversarial tests were updated consistently.

## Document checks

- Markdown lines: 3,750.
- PDF pages: 54.
- Markdown code fences are balanced.
- Display-math delimiters are balanced.
- All 35 Stage-11 reference records remain present and cited.
- PDF preflight passed: openable, unencrypted, searchable, and non-XFA.
- All 54 pages rendered successfully at 150 dpi.
- Six contact sheets covering every page were visually inspected for clipping, overlap, malformed equations, broken glyphs, and pagination defects.
- PDF text extraction confirms the revised persistent objects and contract terms are present.

## Code and package checks

Tree hashes are identical between revisions 14 and 15:

```text
mdstats/
21fed5596d62c77074a9bd5bc1186bfc37c13eadee588eb541297c045fc43c34

tests/
1795d98b25d6c0763c119acc95af8b5de6d2fa52ea9ec13f943b9eb2b29b8461
```

Only planning/documentation files are changed. Stage C0A1 remains the next implementation stage.
