# Natural-Tiling Candidate Certification Implementation Audit

Version: `mdstats 0.19.24a0`  
Stage: 10A

## Implemented boundary

The new `mdstats.analysis.natural_tiling` module certifies caller-proposed
Stage-9 scientific complexes. It does not search for face sets or tile shells.

Implemented records:

- `OrientedCellImage`;
- `CellComplexSymmetryOperation`;
- `PeriodicCellComplexSymmetryAction`;
- `NaturalTilingSymmetryResources`;
- `NaturalTilingCertification`;
- `NaturalTilingCandidate`;
- `NaturalTilingOutcome`; and
- `NaturalTilingCatalog`.

## Properness implementation

The exact full group is accepted only through
`PeriodicNetSymmetryDiscovery`, whose first backend certifies completeness on its
declared collision-free rank-three domain. The action maps scientific
`FacePlacement` identities through the existing primitive-ring action, then maps
each translation-labelled tile boundary chain. A tile image must equal one
translated and optionally orientation-reversed target attaching map.

The implementation validates the complete finite face/tile action against the
normalized group multiplication table and its removed common translations.
Auxiliary face triangulations, tetrahedral partition vertices, and tetrahedra are
absent from the scientific action digest.

## Certification behavior

Candidate state is not compressed into one Boolean. Primitive completeness,
full symmetry, bounded strength, embedded-face evidence, witness compatibility,
cell-complex validity, partition certification, and properness remain separate.

- certified weak selected faces reject a candidate;
- incomplete or truncated strength remains unresolved;
- missing compatibility or partition evidence remains unresolved;
- exact failure of a full symmetry operation certifies improperness; and
- only fully certified proper candidates are eligible.

Scientific candidate identity excludes auxiliary evidence. Evidence receives a
separate digest. Catalog construction deduplicates equal scientific identities,
preserves unresolved and rejected candidates, and reports `NONE`, `UNIQUE`, or
`MULTIPLE` over eligible candidates only.

## External method and original construction

The properness requirement and natural-tiling framing are adapted from Blatov,
Delgado-Friedrichs, O'Keeffe, and Proserpio (2007), DOI
`10.1107/S0108767307038287`. Translation-labelled periodic incidence follows
Chung, Hahn, and Klee (1984), and full exact net symmetry is supplied by the
existing Delgado-Friedrichs/O'Keeffe-derived discovery layer.

The oriented face/tile image model, exact translation-labelled shell matching,
normalized representative composition formula, multidimensional certification
record, two-digest candidate ownership, and ambiguity-preserving catalog are
mdstats-specific constructions.

## Focused defects prevented by fixtures

The tests explicitly guard against:

1. treating a supplied subgroup as the full net automorphism group;
2. requiring auxiliary triangulations or tetrahedral meshes to share the
   scientific symmetry combinatorics;
3. ignoring orientation reversal of a face or tile representative;
4. composing normalized periodic operations without subtracting their common
   removed translation;
5. equating absent evidence with scientific rejection;
6. declaring bounded `STRONG_IN_DOMAIN` to be unbounded global strength;
7. duplicate candidates caused only by different auxiliary certificates;
8. enumeration-order selection among multiple candidates; and
9. creation of essential rings from rejected or unresolved candidates.

## Deferred work

- Stage 10B natural face selection and local splitting;
- Stage 10C primitive-ring-bound refinement and full downstream rebuild;
- Stage 10D LTA end-to-end validation;
- automatic face-sector propagation;
- automatic periodic tetrahedralization; and
- tile geometry, cages, and portals.
