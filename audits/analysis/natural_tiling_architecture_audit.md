# Framework/Ring Architecture Revision 16 Audit

## Scope

This audit covers revision 16 of `docs/arch_manuals/framework_ring_architecture.{md,pdf}`.
The revision changes documentation and release metadata only. Runtime source, public
APIs, serialized schemas, the primitive-ring specification, and Stage 4R are unchanged.

## Geometric broad phase

The periodic spatial backend is query-agnostic. It accepts continuous lifted
supports, generates complete periodic image candidates, optionally uses an
automatic extended-object linked-cell grid, and leaves distance, intersection,
penetration, linking, containment, and tile-volume overlap to consumer predicates.
Multi-bin occupancy retains image shifts and valid self-images.

## Verlet reuse

The fixed-connectivity vertex-displacement theorem and deformation-aware S3 margin
are reused as a shared validity kernel. The kernel does not inherit atomic
unique-image/MIC semantics; extended-object caches may retain multiple explicit
periodic images. Non-distance predicates require a proved buffered conservative
support rule.

## Face identity and linking

Scientific `FacePlacement` is separated from auxiliary `FaceEmbeddingWitness`
triangulations. Nonzero algebraic ring--spanning-surface intersection certifies
linking. Intersection of two chosen spanning disks means witness incompatibility,
not automatically intrinsic catenation. Disjoint embedded disk witnesses certify
unlinking in the supported two-component disk-bounding case. Zero linking number or
bounded disk-search failure is not promoted to a complete theorem.

## Tile overlap

Tile overlap is interior-volume intersection. Prescribed shared boundaries are
valid; improper crossings and containment overlap are invalid. Boundary
intersection must therefore be supplemented by containment or equivalent
filled-volume classification. The separate partition certificate remains the
authoritative no-void/no-overlap proof.

## Properness

Properness is evaluated on scientific face placements, attaching maps, and tile
orbits. Auxiliary face triangulations and partition meshes need only certify that
scientific structure and need not share identical symmetry combinatorics.

## Attribution

Revision 16 adds Quentrec-Brot for linked-cell neighbor search and Hsieh-Kauffman-
Tsau for intersection-theoretic linking algorithms. The continuous-lift extended-
object adaptation, query-specific support rules, multi-image Verlet adaptation, and
scientific-face/witness split are `mdstats` design contributions.

No executable source changes are introduced by this architecture revision.
