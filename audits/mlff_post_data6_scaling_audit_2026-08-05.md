# MLFF post-DATA6 scaling audit — 2026-08-05

## Observed symptom

After the last DATA6 frame, the campaign emitted no useful progress for a long
period. The delay combined DATA6 finalization, DATA6 evidence assembly, DATA7
selection/fitting, and DATA8 materialization, so it appeared that DATA6 itself
was stuck.

## Superlinear defects found

1. **Unbounded fitted-metric FPS** — the selection code recomputed distances
   from every remaining candidate to every selected candidate at every step and
   produced a complete `N`-frame ordering. This is `O(N^3 d)`.
2. **Atomic-environment FPS** — the environment queue ranked every atomic
   environment, potentially millions of rows, even though the output selects
   frames and only the largest requested frame ladder is consumed.
3. **Coverage distance loops** — candidate coverage repeated Python-level
   nearest-distance calls for each ladder.
4. **Growing DATA6 checkpoint rewrites** — already fixed in the preceding
   revision with an append-only journal; the old sum of checkpoint sizes was
   `O(N^2)`.
5. **Per-domain model-evidence rebuilding** — DATA6 rebuilt frame indexes and
   canonical-domain sets for every domain, yielding `O(DN + D^2)` orchestration
   plus duplicated raw prediction retention.

## Multiplicative and memory defects found

- DATA7 was recomputed for every training seed and mode even though DATA7
  scientific products are seed- and mode-independent.
- Scalar foundation energies were reread from all NPZ prediction sidecars after
  the same predictions had already been authenticated and summarized in DATA6.
- Full prediction force arrays were retained in an unbounded cache, risking swap
  and nonlinear wall-time degradation.
- Checkpoint-bound MACE descriptor sidecars were reread and reduced separately
  for every overlapping final/fold DATA7 domain.
- DATA7 JSON files were written, reread for SHA-256, parsed for restart
  verification, discarded, and then parsed again for immediate DATA8 assembly.
- LTA coverage labeling scanned every atomic environment in the complete
  candidate corpus although only the bounded selected ladder consumes labels.
- Large DATA6/DATA7 objects were repeatedly converted, hashed, and serialized.
- Newly promoted DATA8 trees were immediately rehashed a second time.
- Several sidecars were read once for SHA-256 and again for parsing.

## Implemented redesign

- Exact incremental maximin FPS with one nearest-distance vector and a hard stop
  at the largest requested ladder: `O(N K d)`.
- Frame-level environment aggregation and bounded FPS instead of complete
  atom-level ordering.
- Chunked vectorized candidate coverage and `K x K` selected-neighbor analysis.
- Hash-set membership and heap-based bounded ranking.
- One indexed pass for all DATA6 prediction/difficulty domains and prompt release
  of force arrays after compact summaries are built.
- Lineage-keyed shared DATA7 artifacts reused across seeds, modes, and process
  restarts; DATA8 remains variant-specific.
- Foundation energies reconstructed from compact DATA6 evidence, with sidecar
  fallback only for genuinely missing summaries.
- One shared frame-array index and one per-frame/species MACE-summary cache are
  reused across overlapping DATA7 domains; domain-local fitting remains
  independent.
- Newly streamed DATA7 JSON is hashed during the write, verified bundles are
  retained for immediate DATA8 use, and descriptor-summary memory is released
  before DATA8 assembly.
- LTA environment-class coverage uses the provider's frame index and touches
  only selected frames instead of scanning the complete atom-environment table.
- Streaming DATA6 persistence, cached immutable digests, one-read sidecar
  verification, and no redundant immediate DATA8 tree rehash.
- Explicit progress messages for checkpoint compaction, manifest construction,
  DATA6 evidence assembly, campaign persistence, energy preparation, DATA7
  domain build/reuse, and DATA8 assembly.

## Resulting scaling

For fixed feature dimension, fixed fold count, and largest selection size `K`,
post-DATA6 scientific work is linear in frame count except for bounded
`O(K^2 d)` selected-neighbor reporting and small domain/variant bookkeeping.
PCA/SVD remains `O(N p^2)` for fixed input dimension `p`, which is linear in
`N`; it is a legitimate fitted-metric cost rather than a growing-history defect.

The shared DATA7 cache changes repeated variants from `O(V D N)` scientific
recomputation to one `O(D N)` build plus variant-specific DATA8 materialization.
Within that one build, descriptor reduction changes from repeated domain reads
to one read per frame/species signature in the invocation. Remaining DATA7
artifact serialization is linear in the amount of evidence deliberately
retained by the native schema.
