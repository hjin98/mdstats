# mdstats 0.20.210a0 patch notes

## REPLAY-UNIFY1 architecture freeze

- Freeze the five-gate single-source replay migration before positive FINAL-GPU1 execution.
- Make one selected `[paths].replay_set` the future external replay authority with default deterministic `5:1` / seed-42 train:monitor splitting.
- Separate replay source indexing, label prediction/cache, qualification, split membership, and MACE materialization into independently invalidated layers.
- Freeze independent `source_true` and `foundation_pseudolabel` namespaces so pseudo labels never overwrite source truth internally.
- Mark the revision-76 FINAL-GPU1 workstation bundle archival; regenerate the one-shot release bundle after REPLAY-UNIFY1E.

## REPLAY-UNIFY1A

- Add versioned `mdstats.replay-geometry-identity.v1` using atom-order-preserving 1e-8 Angstrom Cartesian/cell quantization and explicit PBC without reinterpreting historical replay artifacts.
- Add streamed `ReplaySourceArtifact` with source-file SHA-256, canonical geometry identities, source-order identity, atomic-number inventory, and source true-label inventory.
- Add immutable `ReplaySplitManifest` with seeded SHA-256 rank membership, qualification binding, normalized ratio, exact disjointness/union validation, and content-addressed serialization.
- Add `ReplaySingleSourceConfig` and campaign-mapping parser with 5:1/seed-42 defaults and fail-closed rejection of mixed `replay_set` plus legacy split paths.
- Preserve all current ReplayPreparationPlan/DATA8/TRAIN2 behavior until REPLAY-UNIFY1D.
