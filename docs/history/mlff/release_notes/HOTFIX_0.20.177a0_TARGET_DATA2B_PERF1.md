# HOTFIX 0.20.177a0 — TARGET-DATA2B-PERF1

Date: 2026-08-15

## Scope

Performance-only hardening of TARGET-DATA2B hierarchical reference-mass coverage construction before VRAM1. Scientific coverage semantics, schemas, thresholds, family definitions, frame roles, and persisted authority identity are unchanged.

## Bottleneck

For every continuous coverage family, TARGET-DATA2B computes an exact correlation-weighted local k-neighbor radius for every reference frame. At the default beta=1/128 and 36,408 frames, the initial cKDTree query requests about 429 neighbors per frame. The previous implementation forced `cKDTree.query(..., workers=1)` and accumulated weighted neighbor mass one Python row at a time.

## Changes

- vectorized weighted-mass accumulation over bounded row blocks;
- bounded native cKDTree query parallelism;
- new runtime-only `[performance].target_coverage_workers` control;
- automatic mode (`0`) respects the configured CPU budget and caps TARGET-DATA2B tree queries at 8 native threads;
- explicit positive worker counts may request more, subject to machine-visible CPU availability;
- vectorized structural missing-mask filtering;
- per-family TARGET-DATA2B structural progress messages;
- worker count is deliberately excluded from TARGET-DATA2B scientific policy and persisted authority identity.

## Exactness / qualification

The optimized local-radius implementation was compared against the pre-hotfix scalar algorithm with duplicate points, nonuniform correlation-unit weights, and leave-one-out mass normalization. Results are bit-identical. A full TARGET-DATA2B reference rebuilt with one worker and two workers also serializes identically and has the same content digest.

Focused qualification: 51 passed (TARGET-DATA2B coverage/specification, TARGET-DATA2C ladder, TARGET-DATA2D convergence, TARGET-DATA2E production corpus, and relevant campaign prepare/config tests).

Synthetic 36,408-frame / 7-dimensional family benchmark on the constrained qualification host:

- pre-hotfix scalar / one worker: 9.862 s
- optimized vectorized / one worker: 9.567 s
- optimized vectorized / four workers: 2.845 s
- four-worker speedup versus pre-hotfix: 3.47x
- local radii: bit-identical

The benchmark is illustrative only; production speedup depends on CPU topology, family dimensionality, and the number of coverage families.
