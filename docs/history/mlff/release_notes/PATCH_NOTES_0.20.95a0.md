# mdstats 0.20.95a0 patch notes

## Immediate evaluated-model reconciliation

0.20.94a0 selected checkpoints per run as soon as their shortlisted evaluations were complete, but target-head publication was still delegated to a single asynchronous export thread. The public `.model` file could therefore lag a fully evaluated run, export failures were only surfaced after the campaign-wide inference queue drained, and restart recovery depended on re-entering that transient async path.

0.20.95a0 makes publication part of durable per-run finalization. After the last required checkpoint evaluation for a run is committed, mdstats deterministically selects the checkpoint, atomically exports `models/<run-id>-target.model`, and immediately commits `evaluated_model:<run-id>` before the parent result callback continues. The adaptive inference executor already refills empty GPU slots before invoking result callbacks, so this synchronous filesystem work does not intentionally starve admitted inference concurrency.

## Restart behavior

At evaluation startup, cached checkpoint evaluations are authenticated and loaded into the run context. A run whose complete shortlisted evaluation set is already present is finalized before any new inference queue is launched. Therefore a campaign interrupted after checkpoint evaluation but before parent-level publication is repaired simply by rerunning `evaluate`, including the case where there are zero new checkpoint tasks.

If target-head export fails, `selection:<run-id>` remains durable, the selected checkpoint reconstruction cache is retained, and the transient in-memory `selection_finalized` flag is not set. The next `evaluate` invocation retries publication rather than silently treating the run as complete.

## Compatibility

No evaluation-policy, checkpoint-selection, metric, protocol, or verification scientific identity changed. Existing evaluation rows and selections remain reusable after their normal provenance checks.
