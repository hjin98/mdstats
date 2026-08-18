# MLFF-DATA9B4 storage lifecycle and durable restart specification

## Scope

This specification governs automatic reclamation of campaign artifacts and the
persistence/recovery contract for long-running MACE training.

## Safety invariants

1. A current materialization root, current DATA8 generation, live training run,
   selected checkpoint, or checkpoint needed by incomplete evaluation shall not
   be deleted.
2. Every deletion shall be justified by current SQLite reachability, immutable
   materialization identity, stage completion, or superseded runtime policy.
3. Destructive cleanup shall retain compact diagnostic evidence when the source
   contained failure logs or runtime history.
4. A successful training record is reusable only after its checkpoint catalog
   is re-inventoried and matches the recorded content digest.
5. An interrupted attempt is audited but shall not consume the scientific
   failure retry budget.
6. Existing checkpoint bytes authorize `--restart_latest`; their existence does
   not depend on whether the parent committed the prior attempt to SQLite.
7. No second campaign parent may supervise a run with a live child-process
   marker.

## Lifecycle classes

### Immutable/current

Current DATA3-DATA8 records, current materialization roots, DATA8 live
symlinks/generations, target/replay artifacts, completed run records, selected
checkpoint bytes, evaluation metrics, selections, protocol freeze evidence,
and verification evidence are retained.

### Restart-critical

For incomplete runs, all checkpoints, result streams, child logs, run-local
execution records, and active process markers are retained.  On interruption,
children terminate gracefully and the parent commits an `interrupted` record.

### Reconstructable cache

Normalized frame cache, shared DATA7 cache, and heavy bounded preflight outputs
may be deleted only after preflight succeeds.  They can be regenerated from
source and immutable campaign records but are not needed for train/evaluate or
verify continuation.

### Superseded

Unreferenced prior DATA8 generations, stale promotion trees, orphaned external
record payloads, and obsolete runtime-policy archives may be deleted after the
stale-age threshold.  Runtime archives first emit compact diagnostic JSON.

### Post-selection checkpoint bytes

All checkpoints remain until every candidate has an evaluation record and one
checkpoint has been selected.  Thereafter, selected bytes and the complete
metric/catalog evidence remain; only unselected checkpoint bytes are removed.

## Commands

`cleanup --dry-run` reports paths, reasons, and logical reclaimable bytes.
`cleanup` applies the same conservative policy used at automatic lifecycle
boundaries.  `--keep-preparation-caches` and
`--keep-unselected-checkpoints` provide explicit retention overrides.

## Failure behavior

Cleanup failures are reported and never convert a scientifically complete stage
into success by assumption.  SQLite vacuuming is skipped while live children
exist.  Low-disk training returns the stage to `WAITING` after durable child
interruption rather than classifying the scientific run as failed.

## Planned successor roadmap after 0.20.105a0

The lifecycle classes above describe the currently implemented conservative cleanup
behavior. They remain binding until the planned EVAL-MF/STOR gates are implemented.

The successor roadmap is defined in
`mlff_eval_mf_successive_halving_spec.md` and
`mlff_storage_management_spec.md`. In particular, future partial-round evaluation
records are screening evidence rather than complete checkpoint evaluations, and
checkpoint deletion authority will be revised only after STOR2/STOR3 qualify compact
evaluation-state capsules and lifecycle-safe reclamation. No current implementation
may infer those future deletion permissions merely from this planning note.
