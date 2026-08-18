# mdstats 0.20.167a0 - TARGET-DATA2D bounded target-size convergence authority

- New campaign initialization now emits the intentional two-seed production geometry (`2 x (3 CV + 1 final) = 8` runs); existing campaign TOMLs remain unchanged.
- Stage B/C evidence contracts deliberately reject historical adaptive-stop behavior as revised size-study evidence; later TRAIN2/EVAL2/VERIFY gates must generate authenticated 10/30-epoch evidence. Evidence freezes optimizer-update count, structures presented, normalized schedule progress, instantaneous LR, wall time, foundation checkpoint, evaluation role, TRAIN2 policy, and exact checkpoint/optimizer continuation ancestry from Stage B to Stage C.

This release implements the TARGET-DATA2D control and decision authority on top of the frozen TARGET-DATA2A/B/C evidence chain.

## Implemented

- Stage A is executed during campaign preparation. A rung qualifies only when it is materializable and every target label domain passes its TARGET-DATA2B coverage/extent/required-stratum report plus the TARGET-DATA2C mandatory correlation/stratum obligations.
- More than four qualifying rungs are reduced to the four smallest. Three or four are retained unchanged. Fewer than three raises `TargetDataCoverageError`.
- `TargetSizeTrainingEvidence` freezes exact Stage-B 10-of-30 and Stage-C 30-of-30 evidence identities.
- Stage-B ranking is target-only. Replay may be recorded diagnostically but cannot reject, rank, mutate LR, or stop a size-study candidate.
- The unrounded practical-equivalence default is 1.0 meV/A. Deterministic anchored equivalence bands prefer the smaller target set and avoid non-transitive chained pairwise ties.
- Stage C requires target, replay-retention, and physical qualification gates before ranking. Replay has zero ranking credit.
- If the largest bounded-ladder finalist remains materially better by more than the equivalence threshold, the result is explicit non-convergence rather than a false converged size.
- The Stage-A authority is stored in the campaign prepare receipt and authenticated before preflight/training.
- Coverage controls in `[target_data.size_convergence]` now actually configure TARGET-DATA2B (`coverage_metric`, threshold, beta, leave-one-out, Q01/Q99 alpha); changed policy invalidates restart evidence instead of being ignored.

## Intentional gate boundary

TARGET-DATA2D does not route Stage B/C through the historical adaptive-stop trainer. The revised TRAIN2 learning-rate/budget policy and EVAL2/DEPLOY/PES/RELAX/DYN evidence generators are later gates. This release supplies the immutable evidence contracts and deterministic reducer they must satisfy.
