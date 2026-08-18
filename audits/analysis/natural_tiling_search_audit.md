# Natural Face Selection and Master-Refinement Splitting Audit

Version: `mdstats 0.19.25a0`  
Stage: 10B

## Implemented boundary

`mdstats.analysis.natural_tiling_search` performs a complete finite search
relative to one caller-supplied exact Stage-9 master refinement. Every candidate
ring cut must already occur as a scientific interface in the master
`PeriodicCellComplex`, and the matching `PeriodicPartitionCertificate` fixes the
embedded witness and exact tetrahedral arrangement.

The module adds:

- `NaturalTilingSearchResources`;
- `NaturalFaceOrbit` and bounded strength states;
- `NaturalFaceSelection`;
- machine-readable rejection records;
- generated candidate records;
- `NaturalTilingSearchResult` with separate search status and Stage-10A catalog;
- `maximal_face_selections`; and
- `search_natural_tilings_from_master_refinement`.

## Exact search construction

The complete discovered automorphism group partitions master faces into exact
scientific face orbits. Only orbits whose complete ring content is
`STRONG_IN_DOMAIN` are selectable. The implementation transactionally preflights
and enumerates every nonempty subset of these orbits.

For each selection, hard fixed-witness compatibility constraints are checked
before geometry is reconstructed. Selected scientific interfaces are removed
from the tetrahedron merge graph; omitted interfaces and auxiliary facets remain
adjacencies. Each adjacency carries its exact lattice translation.

A quotient traversal assigns a lifted offset to every reached tetrahedron. If the
same quotient tetrahedron is reached with unequal offsets, the closed walk has a
nonzero accumulated translation and the region is periodic and noncompact. Such
slabs or channels are rejected. Zero-consistent components define finite tile
orbits.

The surviving components are converted into exact translated tile placements.
Selected interface triangles reconstruct their oriented tile-shell terms. The
module then rebuilds the Stage-9 scientific complex, re-runs the exact periodic
partition certificate, and applies Stage-10A properness and candidate
certification.

Only inclusion-maximal viable selected-orbit sets survive. Incomparable maximal
alternatives remain explicit; enumeration order is never a scientific
criterion.

## Certification and failure semantics

Search completeness is independent of the resulting natural-tiling catalog.
Resource truncation, unresolved ring strength, and active unresolved
compatibility make the search `UNRESOLVED`. They are never converted into a weak
ring, invalid geometry, or `NONE` natural-tiling theorem.

Every failed selection retains a machine-readable rejection kind and diagnostic.
Scientific candidate identity remains the Stage-10A identity; master-refinement
and search evidence receive their own source-bound records.

## External method and original construction

Full-symmetry locally strong ring selection, splitting by admissible strong
non-face rings, and preservation of legitimate alternatives are adapted from
Blatov, Delgado-Friedrichs, O'Keeffe, and Proserpio (2007), DOI
`10.1107/S0108767307038287`. Translation-labelled periodic adjacency is
compatible with Chung, Hahn, and Klee (1984), DOI
`10.1107/S0108767384000088`.

The certified master-refinement domain, exact coarsening graph, zero-translation
finite-component proof, shell reconstruction, partition replay, maximal finite
selection rule, and explicit unresolved semantics are mdstats-specific
constructions.

## Focused defects prevented

The Stage-10B fixtures guard against:

1. selecting only part of a full symmetry orbit;
2. treating weak or unresolved rings as certified splitters;
3. ignoring higher-order fixed-witness incompatibilities;
4. accepting a periodically unbounded slab as a finite tile;
5. rebuilding shells without translated interface orientation;
6. trusting volume closure without exact partition replay;
7. returning a valid but nonmaximal splitting;
8. collapsing incomparable maximal alternatives;
9. silently changing the master witness assignment; and
10. accepting serialized data whose source replay or digest has been altered.

## Deferred work

- Stage 10C primitive-ring-bound refinement and complete downstream rebuild;
- Stage 10D LTA end-to-end certification;
- automatic construction of the master refinement;
- alternative witness arrangements inside one search;
- arbitrary Steiner surfaces or unbounded ring search; and
- tile geometry, accessible cages, windows, and portals.
