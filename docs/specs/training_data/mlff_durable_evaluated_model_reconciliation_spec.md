# Durable evaluated-model reconciliation

## Requirement

A run with a complete current-policy checkpoint evaluation set must expose its selected target-head model in the campaign parent `models/` directory without waiting for unrelated campaign evaluations. This property must survive parent-process interruption and restart.

## State transition

`evaluation:<run>:<checkpoint>` records are committed individually. Once every checkpoint in the authenticated shortlist has a current reusable record, mdstats computes `selection:<run>`. Publication is synchronous and atomic: the selected checkpoint is materialized (reusing its reconstruction cache when available), the target head is staged beside the public destination, and `os.replace` publishes `models/<run>-target.model`. Only after successful publication is `evaluated_model:<run>` committed and the selected reconstruction cache removed.

A publication exception leaves the durable selection and reconstruction cache intact and does not set the transient finalization flag. Rerunning `evaluate` retries the missing publication.

## Restart reconciliation

Cached evaluation records are authenticated during command startup. Cached-only complete runs call the same finalization routine before `_run_adaptive_inference_tasks` is invoked. Zero pending inference tasks is therefore not an early-exit condition for publication repair.

## Scheduling

The rolling inference scheduler removes completed futures and refills newly empty slots before running per-result callbacks. Synchronous model publication may consume CPU/filesystem time in the parent callback, but admitted GPU slots have already been refilled.

## Non-goals

This change does not alter checkpoint admissibility, ranking, metrics, scientific cache identities, protocol aggregation, committee freezing, or verification acceptance.
