# Embedded Face Placement Audit

Version: `mdstats 0.19.22a0`  
Stage: `8C`

## Implemented boundary

- Added exact rational segment--triangle and triangle--triangle predicates in
  `_robust_geometry.py`, including coplanar degeneracies and exact intersection
  dimensions.
- Added exhaustive, deterministic boundary-vertex polygon triangulation in
  `_surface_mesh.py`, guarded by the exact Catalan count.
- Added `face_candidates.py` with mesh-independent `FacePlacement` identity,
  auxiliary `FaceEmbeddingWitness` certificates, framework-penetration records,
  exact algebraic ring--surface intersection, particular-witness compatibility,
  symmetry mapping, and finite higher-order constraint support.
- Bound every public result to the exact periodic net view, embedding, primitive
  ring catalog, and Stage-8B edge certificate.
- Added deterministic source replay for face, witness-pair, and compatibility
  certificates.

## Scientific safeguards

- A penetrated disk remains an embedded spanning surface but is not an admissible
  framework face witness.
- Nonzero algebraic ring--surface intersection proves linking; zero intersection
  is not promoted to unlinking.
- Intersection of particular disk witnesses proves only witness incompatibility.
- Disjoint embedded disks provide a bounded unlinking witness.
- Shared boundary is allowed only when each exact contact lies on the actual
  common lifted vertex or edge.
- Failure of the finite triangulation family remains `UNRESOLVED`.
- Resource exhaustion raises transactionally before any partial result is returned.

## External algorithmic provenance

- Robust exact-sign policy: Shewchuk (1997).
- Noncoplanar triangle interval decomposition: related to Moller (1997), with
  mdstats exact degeneracy handling.
- Bounded spanning-disk caution: Hass, Snoeyink, and Thurston (2003).
- Simplicial algebraic linking interpretation: Hsieh, Kauffman, and Tsau (2017).

The finite witness family, periodic support composition, source binding, separation
of framework penetration from disk embeddedness, and finite constraint ownership
are mdstats-specific.
