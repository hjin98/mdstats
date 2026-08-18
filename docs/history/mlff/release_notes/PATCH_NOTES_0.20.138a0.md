# mdstats 0.20.138a0

MLCV-VERIFY1 closes the physical-verification and locked-test gate of the conventional-CV redesign.

Qualified FINAL1 final-seed representatives are verified in deterministic FINAL1 order. Physical fallback may advance only to another already-qualified final seed and stops permanently at the first bounded-NVE passer; fold models can never enter this path. The selected target-head bytes are frozen before locked evidence is exposed.

Locked post-freeze target test `E` is then materialized and evaluated on that exact frozen model only. `E` is target-only, has no replay or fallback authority, and a failure records campaign failure/scientific-review evidence rather than selecting another seed or checkpoint. `models/production_best.model` is published atomically only when both physical verification and locked `E` pass.

New TOML uses `fallback_to_next_qualified_final_seed = true`. Historical `fallback_to_next_full_evaluation_candidate` remains supported for pre-MLCV ADAPT-VERIFY1 campaigns. Verification policy identity freezes physical thresholds, learned-model dtype, locked-E target ceiling, and retained safety-metric policy.

MLCV-MIGRATE1 remains the next and final planned gate.
