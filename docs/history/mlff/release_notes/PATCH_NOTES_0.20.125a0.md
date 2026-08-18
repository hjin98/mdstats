# mdstats 0.20.125a0 patch notes

## ADAPT-RANK1 — zero-new-inference lightweight run champions

This release implements the fourth gate of the post-0.20.120 adaptive MLFF revision.

### One champion per admissible run

After adaptive training completes, mdstats consumes only the persisted ADAPT-STOP1 epoch history
and the already-frozen checkpoint catalog. Epochs outside the target/replay candidate rectangle are
rejected before scoring. Eligible epochs use the configured weighted target/replay force-RMSE score;
the default 1:1 score is the arithmetic mean.

Each run with at least one admissible epoch freezes exactly one
`lightweight_run_champion.json`. Deterministic ties prefer lower target RMSE, then lower replay RMSE,
then earlier epoch and checkpoint SHA-256. A run that never entered the admissible region records an
explicit no-champion outcome instead of selecting its final epoch.

### Zero inference and exact reconciliation

ADAPT-RANK1 accepts frozen evidence objects rather than checkpoint paths. It launches no MACE
inference and does not deserialize model checkpoints. The ranking artifact is bound to the run plan,
training protocol, adaptive-stop state/policy, checkpoint catalog, and common ADAPT-MON1 target and
true-replay monitor identities. Missing ranking evidence can therefore be reconstructed exactly after
an interrupted parent process without reopening model bytes; changed ranking evidence fails closed.

### Gate boundary

ADAPT-EVAL1 remains pending. The current EVAL-MF evaluator is still runtime-authoritative in
0.20.125a0; the next gate will replace successive halving with campaign-wide top-K screening over
these run champions followed by authoritative full target/true-replay evaluation.
