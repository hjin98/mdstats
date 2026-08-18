# MLFF architecture revision 26 - ADAPT-MON1 implementation

This release implements `ADAPT-MON1` from revision 24 on top of the ADAPT-PREC1 runtime
closed in revision 25. It changes online monitor construction/identity only; adaptive stopping
and the simplified finalist evaluator remain later gates.

Implemented contract:

- fixed common target online monitor, default 256 configurations, selected deterministically from
  DATA5 `outer_monitor` evidence with condition/run balancing and source-time systematic coverage;
- fixed independent replay online monitor, default 512 configurations, selected only from
  `TRUE_DFT` replay evidence with chemistry/size-aware systematic coverage;
- exact monitor membership and lineage bound into production materialization, DATA8, and training
  protocol identities;
- identical target-monitor membership for all competing folds/seeds/final-development jobs;
- multi-head `pt_valid_file` points to the materialized true-label replay monitor while replay
  gradient training remains configured independently;
- monitor evidence never supplies gradients and locked evidence never leaks into monitor roles;
- ADAPT-PREC1 learned-model dtype is preserved during monitor inference, while mdstats-owned
  metric arithmetic remains FP64.

Interim behavior is explicit: 0.20.123a0 still trains to `max_num_epochs` because ADAPT-STOP1 is
not yet implemented, and the historical EVAL-MF evaluator remains runtime-authoritative until
ADAPT-EVAL1.

The canonical contract is documented in
`docs/specs/training_data/mlff_online_monitor_spec.{md,pdf}` and the MLFF architecture manual.
