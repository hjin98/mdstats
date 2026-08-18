# mdstats 0.20.88a0 Patch Notes

## Adaptive evaluation and verification

- Moved telemetry start from the first model forward pass to the first
  computation-heavy stage.
- Evaluation starts at checkpoint authentication/hash/deserialization; direct
  model evaluation starts at artifact authentication.
- Verification starts at MACE model loading/device transfer, or dynamics
  initialization for a prebuilt calculator.
- The 20-second window spans reconstruction, monitor loading, model transfer,
  inference, NVE integration, and metric reduction without stage resets.
- Concurrency changes, telemetry loss, and unsignaled replacement workers still
  reset calibration.

## Training window

- Adaptive training now defaults to a 60-second true-epoch window.
- The exact prior generated 180-second value migrates to 60 seconds; custom
  values remain authoritative.

## Progress

- Evaluation and verification print per-task stage transitions.
- Periodic scheduler messages summarize the current stages of all active jobs.

## Compatibility

- Evaluation/verification shared defaults of 10 seconds (0.20.86a0 legacy) and
  60 seconds (0.20.87a0 canonical) migrate to 20 seconds.
- Explicit phase-specific and other custom values remain unchanged.
- Scientific evaluation, selection, export, and verification-case identities
  are unchanged.
