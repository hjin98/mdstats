# mdstats 0.20.87a0 patch notes

## Corrected inference admission telemetry

- Added an explicit worker-local first-forward signal for adaptive checkpoint
  evaluation and bounded NVE verification.
- Excluded checkpoint conversion, monitor loading, model/calculator construction,
  CUDA initialization, velocity initialization, and other setup work from runtime
  admission telemetry.
- Checkpoint evaluation signals immediately before its first batched MACE prediction.
- NVE verification signals immediately before its first force or energy evaluation.
- Required every active worker at the current concurrency level to enter true
  inference before calibration begins.
- Replaced the previous short warm-up with a trailing 60-second true-inference
  telemetry window by default.
- Required sufficient samples to cover the complete window, rather than accepting
  only a small fixed sample count.
- Reset calibration after every concurrency-level change so a newly added job cannot
  inherit earlier measurements.
- Avoided runtime GPU polling during worker setup; only the pre-launch idle baseline
  is sampled before the first forward pass.
- Reset stateful CPU counters at true-inference entry so CPU utilization intervals do
  not span initialization.

## Configuration migration

- Added the canonical
  `parallel_inference_calibration_window_seconds = 60.0` control and phase-specific
  evaluation/verification variants.
- Retained all older `*_stabilization_seconds` keys for backward compatibility.
- Automatically migrate the exact 10-second default emitted by 0.20.86a0 to the
  corrected 60-second window.
- Preserve other legacy custom values unchanged.
- Canonical calibration-window keys take precedence and may explicitly request a
  different duration.

## Compatibility

- Resource ceilings remain 90% CPU, 90% GPU utilization, 90% VRAM, and 80% RAM.
- Evaluation, selection, export, and verification scientific identities are
  unchanged.
- Existing authenticated evaluation records and verification-case caches remain
  reusable.
