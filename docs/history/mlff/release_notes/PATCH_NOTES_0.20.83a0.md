# mdstats 0.20.83a0 — constraint-aware checkpoint evaluation

## Problem

Bounded evaluation correctly evaluated only a small checkpoint shortlist, but `select_checkpoint` still assumed every completed run must contain an admissible candidate. If all shortlisted epochs for one run violated a mandatory stress, focus-force, worst-condition, energy, or replay-retention constraint, the command raised immediately and discarded the opportunity to evaluate and verify other completed folds or seeds. The terse exception also hid which constraints failed.

## Behavior

- Every evaluated checkpoint receives a durable admissibility decision.
- If no candidate passes, the run receives a `selection_failure:<run-id>` record containing epochs, metrics, thresholds lineage, exact rejection reasons, and reason counts.
- The failed run is excluded from model export and verification; evaluation continues with other completed runs.
- Fold evidence is recomputed from runs that both completed training and have an admissible selected checkpoint. A three-fold group may therefore downgrade to partial-cross-validation or single-model evidence.
- A full production freeze is withheld if any configured run lacks an admissible checkpoint, even when training itself completed.
- If no completed run is admissible, evaluation ends in `WAITING` with a consolidated diagnostic rather than a raw stack trace.

## Bounded-evaluation semantics

When only four of thirty epochs were evaluated, failure means only that the four authoritative candidates failed. It does not prove the remaining twenty-six epochs would fail. The diagnostic says this explicitly. Set `[evaluation].max_checkpoints_per_run = 0` for exhaustive evaluation only when the additional cost is justified. Mandatory thresholds are never silently relaxed and an inadmissible checkpoint is never exported as a production model.

## Restart

Completed checkpoint metrics are cached. Install this release and rerun `evaluate`; the four expensive evaluations already completed for the affected run are reused. No `prepare`, preflight, or retraining is required.
