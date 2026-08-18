# mdstats 0.20.124a0 patch notes

## ADAPT-STOP1 — weight-coupled adaptive training termination

This release implements the third gate of the post-0.20.120 adaptive MLFF revision.

### Default stopping geometry

The global target force-RMSE boundary is 30 meV/A. With default 1:1 target:replay score weights,
the replay boundary is also 30 meV/A. Training stops after a durable epoch checkpoint when target
RMSE reaches 80% of its boundary (24 meV/A), replay RMSE reaches 120% of its derived boundary
(36 meV/A), or the 30-epoch hard ceiling is reached.

### No additional monitor inference

ADAPT-STOP1 consumes the fixed 256-target/512-true-replay validation rows already produced by
MACE each epoch. The stop decision is installed inside the qualified MACE 0.3.16 loop after the
epoch checkpoint is durable, so threshold termination exits normally and still permits MACE final
model publication.

### Replay feasibility and restart safety

The initial true-label replay validation freezes the foundation replay baseline before epoch 0.
Replay-heavy weight choices whose derived replay ceiling falls below that baseline fail closed
unless explicitly overridden. Run-local `adaptive_training_stop.json` records the immutable
policy digest, foundation baseline, per-epoch target/replay RMSE, candidate eligibility, and
terminal reason. Checkpoint restart requires matching state. A terminal restart skips the epoch
loop and finalizes without training an extra epoch.

### Gate boundary

ADAPT-STOP1 records whether an admissible epoch exists but does not choose it. ADAPT-RANK1 is the
next gate. EVAL-MF remains the current production evaluator until ADAPT-EVAL1.
