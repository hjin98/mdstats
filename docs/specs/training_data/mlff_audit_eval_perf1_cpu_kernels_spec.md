# AUDIT-EVAL-PERF1 Foundation Audit and EVAL2 CPU-kernel specification

## Status

Implemented in mdstats 0.20.233a0 / MLFF architecture revision 100.

## Scientific invariants

AUDIT-EVAL-PERF1 is an exact-equivalence execution gate. It MUST NOT change:

- foundation-model checkpoint/head identity, prediction bytes, or DATA6 prediction-manifest authentication;
- FOUNDATION-AUDIT1 development-domain membership, metric semantics, conditioned structural channels, probe contracts, or persisted audit schema;
- EVAL2 target-role membership, checkpoint shortlist/admissibility/ranking authority, target metric definitions, block identity, bootstrap seed material, or persisted record schemas;
- replay hard-admissibility semantics;
- MACE-MPA-0 versus MACE-MH-1 model-family behavior;
- GPU inference/training numerical authority.

No model inference is authorized by this gate. FOUNDATION-AUDIT1 MUST continue to reduce the already completed DATA6 prediction sweep, and EVAL2 CPU changes begin only after prediction objects/artifacts already exist.

## EVAL2 static-reduction metadata

Repeated checkpoint evaluations over the same immutable `EvaluationDatasetView` MAY cache execution-only metadata keyed by the in-memory view identity and ordered correlation-block IDs. The cache contains only reconstructible indexing state:

- per-frame composition keys;
- sorted species inventory and per-frame species local indices;
- per-frame focus/non-focus masks;
- sorted block labels and compact per-frame block codes.

The cache MUST NOT enter target-role, prediction, checkpoint, or metric scientific identity. Cache eviction or disabled caching MUST reproduce the same persisted metric record.

Force-vector tail storage is preallocated from the immutable view atom count. Species, condition, group, block, stress, and global SSE accumulation preserve historical frame order and scalar update order where those values feed persisted authority.

## Paired bootstrap

The paired EVAL2 block bootstrap MUST preserve:

- the existing seed derivation;
- NumPy `default_rng` draw stream;
- identical paired block draws for both candidates;
- current confidence-interval and practical-equivalence decision semantics.

Replicates MAY be generated in bounded 2-D batches. Batch size is an execution choice derived from block count and a 32 MiB temporary-memory target, capped at 256 replicates. Changing batch size MUST NOT change the persisted `Eval2BootstrapComparison` record.

## FOUNDATION-AUDIT1 reduction

One `build_foundation_target_audit` call SHOULD construct the DATA3 frame-array index once and reuse it across all audit domains. Per-run atomic-number membership MAY likewise be pre-indexed once and shared across domains. These caches are execution-only.

The reducer MAY reuse an already computed `delta * delta` array for global and per-species SSE and MAY evaluate configured force-tail quantiles in one NumPy call. Prediction-sidecar verification, force/stress shape checks, memmap spill behavior, structural conditioning, and warning behavior remain unchanged.

## Acceptance authority

Same-host paired evidence against untouched 0.20.232a0 records:

- EVAL2 target metric reduction, 4,096 configurations / 294,912 atoms: approximately 0.862 s -> 0.449 s median (~1.92x) with exact metric digest `d9dd9db2c2d47e2d6f034e0b58f094c04c516d5a0dc4f0089d3f15762d434658`;
- paired bootstrap, 768 independent blocks / 2,000 replicates: approximately 0.0512 s -> 0.0152 s (~3.36x) with exact comparison digest `9664354fd2d871e67113ff5b9ef28118c9414a59f29a5fd4114acb729590397e`;
- available no-inference FOUNDATION-AUDIT1 fixture: approximately 0.0580 s -> 0.0545 s (~1.06x), exact audit digest `39b8b207c741798f5a8555b41ceb0c746948935612d84d45961ba87b0e8c94e5`, and unchanged model-provider call counts 44 descriptor / 44 prediction calls.

Timing is execution evidence. Exact persisted records and no-additional-inference behavior remain scientific authority.

The next optimization gate is `REPLAY-PERF1`.
