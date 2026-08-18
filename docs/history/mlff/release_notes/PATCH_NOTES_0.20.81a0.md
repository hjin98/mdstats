# mdstats 0.20.81a0 — MACE training-checkpoint reconstruction for evaluation

## Failure fixed

MACE 0.3.16 epoch checkpoint files (`*.pt`) are restart checkpoints, not
serialized deployable model objects.  They contain a dictionary with model,
optimizer, and learning-rate-scheduler state.  Passing such a file directly to
`MACECalculator` produced:

```text
AttributeError: 'dict' object has no attribute 'to'
```

The consolidated TorchScript deprecation warning printed immediately before the
traceback was not the cause of the failure.

## Exact reconstruction contract

Evaluation now distinguishes whole serialized MACE models from optimizer
checkpoints.  For an optimizer checkpoint it reconstructs a deployable model by
replaying MACE's qualified restart/export path against the immutable DATA8 job
configuration:

1. Verify the selected checkpoint SHA-256.
2. Copy, never hard-link, the checkpoint into an isolated reconstruction tree.
3. Recreate the exact job configuration and request restart at the checkpointed
   epoch without performing an additional optimization epoch.
4. Ask MACE to write a CPU-serializable whole model.
5. Verify that the resulting payload is a model object accepted by
   `MACECalculator`.
6. Verify again that the original restart checkpoint bytes did not change.
7. Cache the reconstructable whole-model artifact with source/config/checkpoint
   identities, then remove it after evaluation/export or normal cleanup.

The original optimizer checkpoint remains the authoritative restart artifact and
is never replaced by the reconstructed model.

## Evaluation and export

`evaluate_mace_checkpoint` now uses two explicit paths:

- the raw checkpoint path for campaign lineage and checkpoint-byte validation;
- the reconstructed whole-model path for calculator construction.

Target-head export uses the same reconstructed model.  Multi-head models are
strictly reduced to the requested target head.  A genuinely single-head naïve
fine-tuning model is reserialized directly because MACE's `select_head` utility
correctly refuses a model that has only one head.

## Integrity behavior

Cached reconstructed models are accepted only when their sidecar binds the
exact checkpoint SHA-256, immutable DATA8 configuration SHA-256, job identity,
MACE reconstruction contract, and model SHA-256.  Changed inputs invalidate the
cache.  Raw dictionaries presented to a calculator now raise a specific mdstats
input error explaining that reconstruction is required.

## Resume

Install 0.20.81a0 and rerun `evaluate`.  Do not rerun `prepare`, preflight, or
training.  Completed and interrupted training checkpoints remain unchanged.
