# mdstats 0.20.74a0 campaign storage lifecycle and durable training restart

## Purpose

Long MACE campaigns can accumulate tens of gigabytes of duplicated preparation
caches, obsolete DATA8 generations, preflight smoke artifacts, failed runtime
trees, and unselected optimizer checkpoints.  At the same time, cleanup must
not destroy the exact files needed to continue an interrupted run or prove that
a completed run must not be recalculated.

This release adds a conservative, lineage-aware garbage collector and closes
parent/child interruption windows in production training.

## Automatic cleanup

Cleanup now runs at safe campaign boundaries (`train` start/end, successful
`evaluate`, and successful `verify`).  A manual command is also available:

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml cleanup --dry-run
python tools/mdstats-mlff-campaign.py --config campaign.toml cleanup
```

The collector removes only artifacts proven not to be current continuation
inputs:

- orphaned external SQLite record payloads not reachable from any current
  record pointer;
- obsolete, unreferenced DATA7/DATA8 materialization roots and prior promoted
  DATA8 generations;
- stale promotion staging/link/legacy/corrupt trees;
- normalized frame and shared DATA7 caches after preflight, because production
  train/evaluate/verify consume promoted immutable DATA8 data instead;
- large preflight smoke models, checkpoints, copied subsets, and predictions
  after the smoke record passes, while retaining its configuration, logs, and a
  compact checksummed diagnostic summary;
- obsolete execution-policy runtime trees after preserving file inventories and
  log tails in compact JSON diagnostics;
- old orchestration events beyond the configured retention count, followed by a
  safe SQLite `VACUUM` when no live training child exists.

A minimum stale age protects recently interrupted staging trees.  Active run
roots and current materialization pointers are never garbage-collected.

## Checkpoint retention

Before checkpoint evaluation finishes, every training checkpoint is retained:
all candidates may still be needed for selection.  Once every candidate has a
stored evaluation and the protocol selects one checkpoint, the campaign keeps:

- the selected checkpoint bytes for restart, deployment, and diagnostics;
- the complete original checkpoint catalog and SHA-256 identities;
- all checkpoint metric records and the selection decision;
- execution logs and the compact successful execution record.

Only evaluated, unselected optimizer snapshots are deleted.  Evaluation can be
reopened from retained metric evidence without pretending the removed snapshot
bytes still exist.

## Durable interruption and completed-run recovery

`Ctrl-C` now requests graceful termination of every active MACE process group.
The parent waits for child shutdown, writes an `interrupted` attempt record, and
leaves any checkpoint already written by MACE intact.  Interrupted attempts do
not consume the bounded failure retry budget.  The next `train` invocation adds
`--restart_latest` whenever checkpoint bytes exist.

Each active child writes `active_process.json`; a second campaign parent refuses
to launch a duplicate run while that PID is alive.  If the parent disappears
after the child has completed but before SQLite is committed, restart recovers
the run-local `training_execution.json`.  If even that final commit was missed,
a valid final MACE model plus a checksummed checkpoint catalog is promoted to a
successful execution record without repeating epochs.

A recorded successful run is re-inventoried and SHA-256 verified before it is
skipped.  mdstats will not overwrite or silently recalculate a completed run
whose checkpoint bytes have changed or disappeared.

## Disk-pressure safeguard

During production training, free disk is checked alongside GPU telemetry.  If
free space falls below `execution.minimum_free_disk_gib`, the scheduler stops
admitting work, gracefully interrupts active children at their latest durable
checkpoints, commits resumable records, runs conservative cleanup, and returns
the train stage to `WAITING`.

## Configuration

Existing campaign files need no edits; defaults apply at runtime:

```toml
[cleanup]
enabled = true
stale_age_hours = 6.0
remove_frame_cache_after_preflight = true
remove_shared_data7_cache_after_prepare = true
remove_preflight_heavy_artifacts_after_success = true
prune_unselected_checkpoints_after_evaluate = true
maximum_event_records = 10000
```

Changing `campaign.toml` during an active frozen campaign may affect campaign
identity.  Use the defaults first and invoke `cleanup --dry-run` to inspect the
planned deletion set.
