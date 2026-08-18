# Verlet Cache Source / Specification Consistency Audit

## Normative artifacts

- `docs/specs/analysis/_verlet_cache_spec.md`
- `docs/specs/analysis/_verlet_cache_spec.pdf`

## API alignment

The source and specification agree on:

- `VerletCacheOptions(skin, safety_tolerance, cell_list_options)`;
- `VerletPairCache` immutable CSR candidate storage;
- `NeighborCacheStatistics` fields and derived metrics;
- `NeighborSearchSession(collection, options)`;
- `NeighborSearchSession.build_neighbor_list(...)`;
- `NeighborSearchBackend.VERLET_CACHE` as result provenance only;
- `compute_atomic_connectivity(..., verlet_cache_options=None)`;
- request-keyed caches and fixed-cell-only reuse;
- exact current-frame MIC reevaluation;
- conservative cell-change rebuilds;
- one-pass hysteretic/reference nested thresholds.

## Deliberate exclusions confirmed

No source path implements S3 singular-value deformation validity, species-aware nonaffine margins, automatic backend selection, RDF caching, coordination caching, or bond-angle caching.

## PDF checks

```text
Pages: 14
Searchable: yes
Preflight: passed
Rendered-page inspection: passed
```

## Checksums

```text
Markdown SHA-256: 7d4684d051425a1548e789f72193ac8c4ae58228ee70337e5aa36b9cd9c906ca
PDF SHA-256:      7a0f39828077dc481f289d2b2e87d82e12c2f0cf01584ea69c198334224870e1
```

## Result

No source/specification mismatch was found.
