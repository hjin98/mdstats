# Periodic Cell Complex Implementation Audit

Version: `mdstats 0.19.23a0`  
Stage: 9

## Implemented boundary

The new `mdstats.analysis.periodic_cell_complex` module implements two separate
records:

1. `PeriodicCellComplex`, the scientific translation-labelled quotient cell
   complex; and
2. `PeriodicPartitionCertificate`, an auxiliary exact tetrahedral proof of one
   realization of that complex.

The scientific record owns integer boundary operators, tile attaching maps, and
cellular invariants. Auxiliary vertex and tetrahedron choices are excluded from
its digest. Selected Stage-8C witness digests remain construction provenance only.

## Scientific complex checks

The builder verifies:

- one connected rank-three, index-one periodic net;
- exact view/embedding/ring/face/witness source identity;
- admissible selected witnesses and no active forbidden or unresolved constraint;
- translation-labelled edge, face, and tile boundaries;
- `boundary_1 * boundary_2 == 0`;
- `boundary_2 * boundary_3 == 0`;
- two translated tile-side incidences per face orbit;
- quotient Euler characteristic zero; and
- connected, nonbranching, orientable, genus-zero lifted tile shells.

No local face-sector propagation is presented as certified. Tile shells remain
explicit inputs until a complete construction theorem is specified.

## Partition certificate checks

The first rigorous backend accepts an explicit periodic tetrahedral mesh. It:

- normalizes exact tetrahedron orientation;
- rejects degenerate tetrahedra;
- uses the Stage-8B complete periodic AABB candidate generator;
- classifies exact pair relations with rational separating-axis projections;
- permits disjoint interiors and boundary contact only;
- requires exactly two opposite-oriented incidences per periodic facet orbit;
- distinguishes transformed same-tile internal facets from scientific interfaces;
- matches every interface to exactly one selected Stage-8C witness triangle orbit;
- verifies complete once-only triangle coverage for every scientific tile side;
- reconstructs and compares the induced scientific `boundary_3`; and
- requires positive exact per-tile volume and total primitive fractional volume one.

Volume closure is evaluated only after exact no-overlap and closed-facet gates.

## Defects found during focused implementation

Fixture-driven testing exposed and corrected three defects before release:

1. chain composition returned a tuple of empty columns, whose tuple truth value
   was incorrectly treated as a nonzero chain; validation now uses `any(columns)`;
2. the second tetrahedron at a periodic facet was compared in its untransformed
   tile placement, collapsing opposite tile sides onto one image; the exact facet
   pairing translation is now applied to the second tile placement; and
3. any strictly contained vertex was initially labeled containment even for a
   partial interpenetration; containment now requires all vertices of one
   tetrahedron to lie in the closed other tetrahedron.

A fourth design correction collapses a complete set of auxiliary witness
triangles to one scientific face-side coefficient rather than summing one
`boundary_3` coefficient per triangle.

## External methods and original construction

The quotient translation-label convention is based on Chung, Hahn, and Klee
(1984). Reliable exact-sign geometric decisions follow Shewchuk (1997). The
face-normal and edge-cross-edge tetrahedral separating-axis family is adapted from
the overlap framework of Ganovelli, Ponchio, and Rocchini (2002), but uses exact
`Fraction` projections rather than their optimized floating implementation.

The translation-labelled cellular composition, tile-shell validation, selected-
witness conformity, and separation between scientific complex identity and
auxiliary partition evidence are project-specific constructions documented in the
Stage-9 specification.

## Deferred work

- automatic face-side sector propagation;
- automatic constrained periodic tetrahedralization;
- natural face selection and symmetry pruning;
- properness under the full periodic-net automorphism group;
- local splitting/refinement rules;
- unique/multiple/none natural-tiling orchestration; and
- tile geometry and cage interpretation.
