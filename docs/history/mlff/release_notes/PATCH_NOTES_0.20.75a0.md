# mdstats 0.20.75a0 patch notes

This release corrects three production-training runtime behaviors without changing DATA3-DATA8 scientific artifacts or invalidating completed training runs.

## Progress cadence

The child supervisor must poll the MACE process frequently so `Ctrl-C`, disk-reserve stops, and process exits are detected promptly. In 0.20.74a0, every one-second cancellation poll also emitted a progress callback. The poll remains one second internally, but visible training/scheduler updates now use `execution.training_progress_interval_seconds`, defaulting to 10 seconds.

## Fixed-window scheduler averaging

The adaptive scheduler no longer waits for GPU utilization or VRAM samples to become low-variance. Once every active job is producing fresh optimizer updates, it gathers telemetry for the full `parallel_training_epoch_stabilization_seconds` window (180 seconds by default), averages the samples, and projects one additional job. Promotion requires both projected mean VRAM and projected mean GPU utilization to remain strictly below their configured ceilings (90% by default).

## Failed-runtime storage

Obsolete execution-layout failures are no longer moved wholesale into `obsolete-runtime-*` directories. mdstats now retains only a bounded JSON diagnostic containing execution metadata, a capped inventory, and bounded log tails, then deletes obsolete models, checkpoints, results, and logs immediately. At most five compact diagnostics are retained per run. Existing heavy `obsolete-runtime-*` directories from earlier releases are removed by the normal cleanup command and train/evaluate/verify cleanup boundaries.

Completed run checkpoints, current-policy restart checkpoints, selected models, and evaluation evidence are not removed.
