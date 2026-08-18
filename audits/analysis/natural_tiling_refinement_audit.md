# Natural-Tiling Bound Refinement Implementation Audit

Release: `mdstats 0.19.26a0`

Module: `mdstats/analysis/natural_tiling_refinement.py`

Specification: `docs/specs/analysis/natural_tiling_refinement_spec.{md,pdf}`

## Implemented scope

Stage 10C treats the primitive-ring maximum size as a hard downstream rebuild
boundary. `PrimitiveBoundBuild` rejects mixed-bound source objects and validates
that the induced ring symmetry, bounded strength, face certificates,
compatibility systems, master complexes, partition certificates, Stage-10B
searches, and aggregate Stage-10A catalog all derive from the current primitive
catalog.

The module then constructs bound-independent stable records for:

- primitive rings;
- induced ring orbits;
- bounded strength states;
- translated and oriented scientific faces;
- compatibility systems with source-bound face/witness digests rewritten;
- scientific master complexes with dense face/tile IDs eliminated;
- exact auxiliary master partitions;
- Stage-10B searches;
- natural tilings; and
- essential rings.

Consecutive snapshots are joined by stable category/key identity. Every addition,
removal, and state modification is retained. Primitive-ring removal between two
complete increasing bounds is an invalid monotonicity violation. Incomplete
snapshots remain unresolved even when their represented records appear equal.

## Scientific boundary

The implementation proves only equality or change over the supplied bound
sequence. `stable_tested_suffix_start` is not an extrapolation to untested larger
rings.

The backend does not construct master refinements, map different primitive cells
or net views, or run the LTA end-to-end gate.

## Persistence

Persistent records use canonical JSON and SHA-256 digests. Report loading
reconstructs all snapshots and recomputes every transition; serialized transition
status and change lists are not trusted independently.

The transient rebuild callback and full source objects are intentionally absent
from the persistent report. Source replay remains owned by the respective
upstream stage records.

## External provenance

The natural-tiling context continues to follow Blatov, Delgado-Friedrichs,
O'Keeffe, and Proserpio (2007), DOI `10.1107/S0108767307038287`. Periodic stable
ring/face identities remain compatible with the vector method of Chung, Hahn, and
Klee (1984), DOI `10.1107/S0108767384000088`.

The rebuild transaction, stable-record normalization, monotonicity gate,
transition semantics, and tested-suffix report are project-specific `mdstats`
constructions.

## Focused fixtures

Ten Stage-10C tests cover:

1. unchanged scientific results across different primitive-catalog digests;
2. one independent rebuild callback invocation per increasing bound;
3. rejection of a requested-bound/source-bound mismatch;
4. primitive-ring disappearance as an invalid monotonicity violation;
5. a modified strength state under one stable ring identity;
6. unresolved propagation despite apparent stable keys;
7. transactional bound-count preflight;
8. rejection of duplicate or decreasing bounds;
9. canonical report round-trip reconstruction; and
10. rejection of a tampered serialized transition.

All ten tests pass. The complete focused Stage 4-10C boundary passes with 206
tests; four unchanged heavy Na-LTA upstream gates remain explicitly excluded.
