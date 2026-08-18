# MACE checkpoint-to-model reconstruction

## Serialization distinction

The MLFF campaign treats two MACE artifacts as different objects:

- **Restart checkpoint** — an epoch `*.pt` dictionary containing model state,
  optimizer state, scheduler state, epoch, and restart metadata.
- **Deployable model** — a serialized PyTorch/MACE module implementing `.to()`
  and suitable for `MACECalculator` or target-head export.

A restart checkpoint is authoritative for continuation but cannot be passed
straight to `MACECalculator`.

## Reconstruction lineage

For checkpoint evaluation mdstats reconstructs a deployable model through the
same qualified MACE executable and immutable DATA8 job configuration that
created the checkpoint.  Reconstruction occurs in an isolated directory and
copies the checkpoint so upstream MACE code cannot rewrite the authoritative
restart bytes.  The source checkpoint hash is checked before and after the
operation.

The cache identity binds:

- restart checkpoint SHA-256;
- DATA8 configuration SHA-256;
- job working-directory identity;
- MACE reconstruction contract;
- reconstructed model SHA-256.

The cache is reconstructable and may be deleted by campaign cleanup.  The raw
checkpoint, execution records, selected-checkpoint catalog, and metrics remain
protected.

## Head export

For a multi-head replay model, export must select the configured target head and
verify its identity.  For an unambiguous one-head naïve model, the complete model
is already the target model and is serialized directly; calling MACE's
multi-head selector would be an error.

## Failure policy

mdstats fails closed if:

- the restart checkpoint does not match its catalog hash;
- the DATA8 configuration is missing or changed;
- reconstruction exits unsuccessfully;
- the output is still a dictionary rather than a model object;
- the original checkpoint bytes change;
- a requested target head is absent or ambiguous.

## Planned OPT-EVAL1 migration

The sandboxed restart-through-MACE reconstruction above remains the qualified
fallback through 0.20.96a0; OPT-EVAL1 in 0.20.97a0 now assigns
its replacement the highest priority.  `OPT-EVAL1` will first reuse an authenticated
whole training model when it is state-identical to the selected checkpoint, then
reuse an authenticated checkpoint-model cache, then restore the checkpoint model
state directly into a qualified architecture template.  The current subprocess
reconstruction remains a fail-closed compatibility fallback until numerical
energy/force/stress and head-export equivalence are demonstrated for representative
intermediate and final checkpoints.

This planned migration is performance-only: restart checkpoints remain authoritative
for epoch state, deployment models remain distinct artifacts, source checkpoint bytes
remain immutable, and selected target-head publication remains atomic.



## 0.20.97a0 direct-restoration implementation

The post-first-campaign OPT-EVAL1 migration is now implemented.  Raw MACE 0.3.16
checkpoints are first restored directly into the completed run's whole-model
architecture template.  The direct path requires exact state-dict key, shape, and
dtype compatibility and reproduces CuEq/OEq backend conversion under the shared FX
serialization lock before loading checkpoint weights.  A final checkpoint whose state
already matches the completed training model reuses that model directly.  Intermediate
checkpoints are serialized only into the reconstructable checkpoint-model cache.

Target-head extraction also has an in-process path using MACE's qualified
``remove_pt_head`` implementation.  The legacy ``mdstats-mace-train`` restart-export
and ``mdstats-mace-select-head`` wrappers remain fallback paths for unsupported or
failed direct restoration.  LoRA remains intentionally fallback-only because the
completed whole model contains merged adapter weights while the training checkpoint
contains the adapter architecture.
