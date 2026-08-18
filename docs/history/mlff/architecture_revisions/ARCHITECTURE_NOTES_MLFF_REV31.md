# MLFF architecture revision 31 - ADAPT-MIGRATE1 migration closure

This release implements the final `ADAPT-MIGRATE1` gate and closes the seven-gate adaptive MLFF
campaign revision introduced in 0.20.121a0.

Implemented contract:

- add `ProtocolFreezeAuthorityRecord`, a schema-neutral lifecycle/storage adapter that validates
  either historical committee freezes or adaptive deployment freezes without replacing the original
  scientific freeze evidence;
- add immutable `AdaptiveMigrationRecord` evidence binding EVAL1, VERIFY1, deployment, adaptive
  freeze, generic authority, learned-model dtype, invariant FP64 scientific arithmetic, and preserved
  historical evaluator-record keys;
- reconcile completed 0.20.127 adaptive campaigns idempotently by replacing only the duplicated
  generic adaptive-freeze alias with the new authority record while preserving
  `adaptive_protocol_freeze` and all historical evidence;
- derive evaluator authority from immutable run protocol identity: adaptive STOP1/RANK1 campaigns
  require `adaptive_topk`, while historical campaigns retain their original
  bounded/exhaustive/multi-fidelity semantics and cannot be silently reinterpreted;
- make post-freeze EVAL1 immutable: later `evaluate` commands authenticate/reuse the frozen
  full-evaluation authority rather than creating a second selection history under one campaign ID;
- require schema-valid freeze authority for consequential STOR operations instead of accepting mere
  presence of a `protocol_freeze` key;
- keep `storage report` read-only by reading migration/freeze summary through SQLite `mode=ro`;
- preserve all STOR1-STOR5 ownership, capability-loss, archive, and deletion boundaries; migration
  adds no cleanup authority;
- retain historical EVAL-MF, committee, and staged/refine records as readable campaign evidence;
  retired algorithms cannot silently regain authority over a new adaptive campaign; and
- qualify the completed PREC1->MON1->STOP1->RANK1->EVAL1->VERIFY1->MIGRATE1 lifecycle together,
  including legacy evaluator/precision and storage/restart compatibility.

The canonical contract is documented in
`docs/specs/training_data/mlff_adaptive_migration_spec.{md,pdf}` and the MLFF architecture manual.
