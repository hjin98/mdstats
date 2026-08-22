# MACE checkpoint-to-model reconstruction

## Scope

This note records the current checkpoint-to-model reconstruction boundary used by the MLFF campaign. Exact current runtime behavior remains specification/adapter-owned; this document explains the durable artifact distinction and fail-closed lineage requirements.

## Serialization distinction

The campaign treats two MACE artifacts as different objects:

- **restart checkpoint** — epoch state containing model/optimizer/scheduler/RNG/restart metadata as defined by the current MACE adapter;
- **deployable model** — a serialized model object suitable for the current evaluation/deployment runtime and target-head export.

A restart checkpoint is authoritative for training continuation. It is not implicitly a deployable model.

## Current reconstruction order

Current reconstruction uses the lowest-cost authenticated realization supported by the qualified adapter:

1. reuse an authenticated completed whole-model artifact when it is state-identical to the requested checkpoint;
2. reuse an authenticated reconstructible checkpoint-model cache;
3. restore the checkpoint state directly into a qualified architecture template when exact state-dict/backend compatibility is satisfied;
4. use the current qualified MACE subprocess reconstruction path only when direct restoration is unsupported or fails under the current adapter contract.

These are execution realizations of one current scientific artifact relation. They are not different campaign generations.

LoRA or another architecture whose restart representation cannot be reconstructed safely by the direct path remains on the current qualified fallback path rather than being coerced into a superficially compatible template.

## Reconstruction lineage

A reconstructed model/cache binds at least:

- restart checkpoint digest;
- immutable training/DATA8 job configuration identity;
- qualified architecture-template or subprocess adapter identity;
- precision/backend/runtime identity;
- reconstructed whole-model digest;
- selected target-head identity where applicable.

Reconstruction executes without mutating authoritative restart bytes. Source checkpoint identity is validated before and after any path capable of touching a copied checkpoint.

The reconstructed whole-model/cache is reconstructible execution state. Authoritative checkpoint catalogs, training records, selected-checkpoint records, and scientific evaluation evidence remain protected.

## Target-head export

For a multi-head replay model, export selects the configured target head and verifies its identity through the current qualified adapter. For an unambiguous one-head model, the complete model is already the target model and no multi-head-selection operation is implied.

Target-head extraction may use the current qualified in-process MACE path when supported. Any alternate current fallback must prove the same selected-head identity and numerical/export contract.

## Failure policy

Reconstruction fails closed when:

- the restart checkpoint does not match its catalog/content identity;
- required immutable training configuration or architecture-template identity is missing/incompatible;
- direct restoration has state-dict key/shape/dtype/backend incompatibility;
- a fallback reconstruction exits unsuccessfully;
- reconstructed output is not a valid current model object;
- authoritative source checkpoint bytes change;
- a requested target head is absent or ambiguous;
- reconstructed-model/cache lineage cannot be authenticated.

Unsupported historical campaign/checkpoint schemas do not gain current meaning through this reconstruction path. If an old campaign cannot satisfy the current checkpoint/runtime identity contract, it requires re-preparation or separate forensic handling rather than product-semantic migration.
