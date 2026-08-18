# Deformation-Cache Specification Consistency Audit

## Release

```text
mdstats 0.14.0a3
```

## Documentation form

The normative specification is maintained from one Markdown source and delivered as:

```text
docs/specs/analysis/_verlet_cache_deformation_spec.md
docs/specs/analysis/_verlet_cache_deformation_spec.pdf
```

The PDF was regenerated from the Markdown source, preflighted, rendered in full, and visually inspected.

## Source-to-spec mapping

| Implemented behavior | Source | Normative specification section |
|---|---|---|
| Public option structure and validation | `VerletCacheOptions` | Public data structures |
| Immutable cache schema and arrays | `VerletPairCache` | Public data structures |
| Statistics identities and diagnostics | `NeighborCacheStatistics` | Public data structures |
| Session construction and inspection calls | `NeighborSearchSession` | Public function and method calls |
| Per-frame evaluation signature and result type | `NeighborSearchSession.build_neighbor_list()` | Public function and method calls |
| Exact request identity | `_request_digest()` | Request identity |
| Exact S1 candidate rebuild | `_rebuild_cache()` | Candidate construction; Algorithm |
| Explicit opt-in deformation policy | `VerletCacheOptions.deformation_aware` | Status and stage boundary |
| Condition-number guard | `_validate_deformation_cell()` | Cell validity and numerical constraints |
| Affine map $H_0^{-1}H_t$ | `_deformation_aware_rebuild_reason()` | Deformation-aware validity theory |
| Smallest singular value | `_deformation_aware_rebuild_reason()` | Affine deformation map |
| Continuous fractional reference | `VerletPairCache.reference_fractional_positions` | Nonaffine atomic motion |
| Active species pairs | `_active_species_pairs()` | Active species pairs |
| Species displacement maxima | `_species_displacement_maxima()` | Nonaffine atomic motion |
| Pair margins | `_deformation_aware_rebuild_reason()` | Accepted pair margin |
| Rigid-rotation reuse | singular-value criterion | Affine deformation map |
| Ensemble fallback | `_deformation_aware_rebuild_reason()` | Ensemble policy |
| Exact current MIC reevaluation | `_evaluate_cached_pairs()` | Reuse operation; invariants |
| Request/cache schema v2 | schema constants and digest | Request identity; cache fields |
| Exceptions and hard failure paths | option/cache validators and S1 backend | Exceptions; edge cases and warnings |

## Consistency result

The Markdown specification, generated PDF, source implementation, focused tests, and S3 mathematical audit describe the same policy. The revised specification now explicitly records data structures, function signatures, input and output types, validation constraints, motives, theory, pseudocode, diagnostics, exceptions, complexity, and edge cases. No undocumented tolerance, approximate geometric shortcut, or silent deformation fallback is active.
