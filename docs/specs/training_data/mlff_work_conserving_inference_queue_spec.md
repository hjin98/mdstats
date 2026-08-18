# MLFF work-conserving evaluation / verification queue

Status: implemented in mdstats 0.20.93a0.

## Scope

This specification applies to the outer independent-job executor used by MLFF
checkpoint evaluation and bounded NVE verification. It does not change the scientific
content of an evaluation or verification task and does not change the training
scheduler.

## Requirement

After adaptive admission has selected a target concurrency `C`, the executor is
work-conserving while pending tasks remain:

- if a worker finishes successfully and the active count drops below `C`, immediately
  submit replacement work from the pending deque;
- perform this replacement independently for every completed future returned in one
  completion wave;
- do not wait for a subsequent telemetry polling interval to refill the slot;
- when telemetry raises `C`, fill newly admitted slots in the same scheduler iteration.

The replacement submission happens after the completed future result has been safely
retrieved but before parent-side result persistence and progress finalization. This is
important because those parent operations can be slower than model inference itself.

## Failure semantics

A worker execution failure stops new scheduling as before. A parent-side result
finalization failure also stops further admission. Independent work already running
may complete while the executor drains safely before the campaign raises the error.

## Resource policy

This change does not modify admission estimates or limits. CUDA evaluation and
verification retain the 0.20.92a0 defaults:

- one-job, 300-second calibration;
- independent 1% activity filters for GPU utilization and incremental VRAM;
- discard the highest 5% and average the next-highest 10% (approximately the
  85th--95th percentile band);
- fixed post-calibration GPU-utilization estimate;
- live 90% VRAM hard guard;
- 90% CPU/GPU/VRAM ceilings and 80% RAM ceiling.

CPU evaluation/verification and training retain their existing policies.

## Scientific identity

Queue timing is runtime-only. It does not affect model weights, model predictions,
metric definitions, checkpoint ranking, evaluation/verification cache identity, or
scientific provenance.
