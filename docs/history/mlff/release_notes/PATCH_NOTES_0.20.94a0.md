# mdstats 0.20.94a0 patch notes

## Parallel CuEquivariance evaluation failure

Parallel evaluation could fail with:

`NameError: module is not installed as a submodule`

The exception originates from PyTorch FX module tracing while MACE converts an e3nn
model to CuEquivariance/OEq form. Multiple sibling evaluation threads were allowed to
perform those third-party graph rewrites simultaneously. FX tracing relies on
process-global hooks/state, so one tracer could observe a module belonging to another
model tree.

0.20.94a0 installs an idempotent process-wide serialization guard around only the
MACE accelerator graph-rewrite functions. Model loading, checkpoint I/O, device
transfer, and admitted CUDA inference remain parallel. This prevents overlapping FX
conversion without reverting evaluation to serial execution.

Evaluation failure messages now also include the worker's active stage to make future
parallel-runtime failures easier to localize.

## Immediate per-run selected-model export

Checkpoint selection is no longer deferred until every campaign-wide evaluation task
finishes. As soon as all shortlisted checkpoints for one run have valid metrics,
mdstats deterministically selects that run's checkpoint and starts target-head export
to:

`<workspace>/models/<run-id>-target.model`

This happens while unrelated folds/runs may still be evaluating. A later failure in a
different run does not remove an already-published model. Restarted evaluation reuses
a matching exported-model record when present.

Reconstructed checkpoint-model caches are retained only until the run is selected so
the selected model can be exported without an unnecessary second reconstruction, and
are removed after successful export.

All target-head publication is now atomic: bytes are staged beside the destination and
published with `os.replace` only after successful serialization. An interrupted
export therefore cannot leave a truncated public `.model` or destroy a previously
valid destination.

## Work-conserving completion handling

A completed wave is now removed from the active-future set as a group and every newly
empty worker slot is refilled before result callbacks run. This extends the 0.20.93a0
rolling-queue guarantee to callbacks that may perform run selection or schedule model
publication.

## Compatibility

No scientific evaluation-policy or verification-case identities changed. Existing
TOMLs and valid evaluation caches remain compatible. Early fold/final model export is
an availability feature only; campaign protocol aggregation, committee construction,
verification, and scientific validation remain separate later gates.
