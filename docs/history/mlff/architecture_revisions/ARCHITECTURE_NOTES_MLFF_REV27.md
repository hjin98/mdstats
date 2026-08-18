# MLFF architecture revision 27 - ADAPT-STOP1 implementation

This release implements `ADAPT-STOP1` on top of the binary learned-model precision and fixed
common online monitors established by ADAPT-PREC1/ADAPT-MON1.

Implemented contract:

- target force-RMSE boundary 30 meV/A by default;
- replay boundary derived as `(target_weight / replay_weight) * target_boundary`;
- default 1:1 weighting gives a 30 meV/A replay candidate boundary;
- target-success training stop at 0.80 of the target boundary (24 meV/A default);
- replay-exhaustion stop at 1.20 of the replay boundary (36 meV/A default);
- hard 30-epoch ceiling retained;
- pre-epoch-0 true-replay foundation-baseline feasibility check with explicit override;
- no extra inference: stop decisions reuse normal ADAPT-MON1 MACE validation rows;
- in-process MACE-loop termination only after a durable epoch checkpoint;
- immutable run-local adaptive-stop evidence with exact policy lineage and restart idempotence;
- terminal restart skips further epochs and completes normal final-model publication;
- run outcome distinguishes whether an admissible checkpoint exists, but ranking remains deferred
  to ADAPT-RANK1.

The canonical contract is documented in
`docs/specs/training_data/mlff_adaptive_training_stop_spec.{md,pdf}` and the MLFF architecture
manual. EVAL-MF remains runtime-authoritative until ADAPT-EVAL1.
