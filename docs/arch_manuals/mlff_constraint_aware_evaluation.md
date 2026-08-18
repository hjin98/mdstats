# Constraint-aware partial checkpoint evaluation

mdstats distinguishes three states for a training run: training incomplete, training complete with an admissible selected checkpoint, and training complete with no admissible checkpoint in the authoritative evaluated candidate set. Only the second state contributes a model to protocol aggregation or verification.

Mandatory checkpoint constraints remain fail-closed. Run-level failure is not campaign-process failure: DATA9B records the rejection evidence and continues evaluating independent runs. Available fold evidence is recomputed after admissibility filtering. Production freeze requires admissible selections for the complete configured matrix; otherwise only explicitly interim evidence may be exported.

A bounded shortlist is an evaluation budget, not an exhaustive scientific claim. A failed bounded shortlist records `bounded_shortlist=true`, the evaluated and available checkpoint counts, and exact rejection reasons. Exhaustive evaluation remains opt-in through `max_checkpoints_per_run = 0`.
