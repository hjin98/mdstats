# mdstats 0.20.82a0 — bounded checkpoint evaluation and tiered verification

## Problem

DATA9B evaluation previously reconstructed and performed authoritative monitor inference on every saved epoch checkpoint. A 30-epoch run could therefore trigger 30 full target/replay monitor passes, making evaluation approach training-scale cost. Verification likewise applied the full structure-temperature NVE matrix to every exported fold and final model, reloaded each model for every case, and evaluated expensive diagnostics at every MD step.

## Evaluation policy

Evaluation is now selection-first and bounded:

1. MACE's existing training-time validation history is read without model inference.
2. At most `[evaluation].max_checkpoints_per_run` checkpoints are shortlisted (default 4), always retaining the latest durable checkpoint and candidates representing the best target/replay validation evidence.
3. The authoritative mdstats target, mobile-ion, stress, condition and replay-retention metrics are run only on that shortlist.
4. Final checkpoint selection remains based on the authoritative metrics, not solely on MACE's inexpensive training log.

Set `max_checkpoints_per_run = 0` for exhaustive evaluation of every checkpoint. Full production evaluation may optionally prune screened-out checkpoints after the selected checkpoint and evidence have been committed; interim evaluation preserves all restart checkpoints.

## Verification policy

Verification is now tiered:

- deployment/final models receive the configured full structure-temperature NVE matrix;
- fold-only comparison models receive one bounded stability smoke by default;
- completed case results are content-addressed and reused on restart;
- one MACE calculator stays resident per model across its sequential cases;
- MD integration still executes every step, while energy/force/distance diagnostics are sampled every `[verification].sample_interval_steps` steps (default 10), including the final step.

Short screening cases do not apply the long-trajectory drift threshold; they still enforce finite outputs, minimum-distance and maximum-force stability. Full cases retain all production thresholds.

## New configuration

```toml
[evaluation]
max_checkpoints_per_run = 4  # 0 = exhaustive

[verification]
steps = 2000
screening_steps = 200
sample_interval_steps = 10
# screening_temperature_kelvin = 800.0

[cleanup]
prune_screened_out_checkpoints_after_evaluate = true
```

## Restart and safety

Evaluation and verification case records are cached by model/checkpoint bytes, data bytes, protocol, runtime and numerical settings. Interrupted commands reuse completed work. Existing preparation, preflight and training state is unchanged; install this release and rerun `evaluate` or `verify` directly.
