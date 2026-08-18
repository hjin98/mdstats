# Periodic Spatial and Edge-Intersection Implementation Audit

Version: `0.19.21a0`  
Stage: 8B

## Boundary

- `_periodic_spatial.py` is private derived candidate workspace.
- `PeriodicEdgeIntersectionCertificate` is the public source-bound scientific certificate.
- `PeriodicNetEmbedding` remains the authoritative geometry source.

## Exactness

- Translation ranges are derived from exact lifted support bounds; no fixed image shell is assumed.
- Direct and linked-cell paths finish with exact rational fractional-AABB overlap.
- Segment intersections are evaluated with exact `Fraction` cross/dot algebra.
- Shared contacts are allowed only for identical `LiftedVertexRef` endpoints.
- Certificate deserialization replays candidate generation and every exact predicate.

## Resource safety

Transactional limits cover objects, stencil images, explicit placements, pair checks,
final candidates, linked-cell insertions, and grid subdivisions. No partial candidate
set or partial certificate is returned.

## Scientific result

Na-LTA has 96 projected framework edges. Its authoritative straight-edge embedding
produces no forbidden periodic intersections. Allowed common-vertex contacts are
retained as diagnostics rather than failures.
