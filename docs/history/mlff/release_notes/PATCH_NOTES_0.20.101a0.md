# mdstats 0.20.101a0 patch notes

This release implements **OPT-EVAL4**, the staged MLFF checkpoint-evaluation pipeline.

## Changed

- Split checkpoint evaluation into explicit CPU preparation, accelerator inference, and CPU finalization stages while retaining `evaluate_mace_checkpoint()` as a synchronous compatibility wrapper.
- Pipeline independent checkpoints through bounded preparation and finalization worker pools around the existing adaptive inference scheduler.
- Keep checkpoint materialization and CuEq/OEq/FX conversion inside accelerator admission because those operations may use CUDA; actual graph conversion remains serialized by the existing process-wide conversion lock.
- Reuse one private candidate calculator and one private foundation calculator within each checkpoint inference task; calculators are never shared between concurrent workers.
- Route cache-only metric/relabel evaluation directly from CPU preparation to CPU finalization without consuming an accelerator slot.
- Bound prepared and finalization backlogs so cached graphs/prediction arrays cannot grow without backpressure.
- Start evaluation telemetry at the accelerator stage, excluding monitor parsing/cache lookup and metric/persistence work from GPU calibration.
- Add stage-specific progress messages and per-checkpoint prepare/infer/finalize timing.
- Add `[execution]` controls `parallel_evaluation_prepare_jobs`, `parallel_evaluation_finalize_jobs`, and `evaluation_pipeline_buffer_jobs` (`0` means automatic).

## Scientific compatibility

No model weights, monitor definitions, prediction schemas, metric definitions, replay provenance, checkpoint-selection constraints, or verification semantics change. The MLFF campaign compatibility token therefore remains `0.20.99a0`; existing campaign state, cached evaluations, persistent predictions, and monitor graph shards remain reusable.

## Failure behavior

Stage failures are attributed to CPU preparation, accelerator inference/conversion, or CPU finalization. New work stops after the first failure, already admitted work is drained safely, and no partial evaluation record is committed before finalization succeeds.
