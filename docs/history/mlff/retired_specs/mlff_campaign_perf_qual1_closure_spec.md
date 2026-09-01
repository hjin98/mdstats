# CAMPAIGN-PERF-QUAL1 end-to-end optimization closure specification

## Status

Implemented in mdstats 0.20.235a0 / MLFF architecture revision 102. The gate passes integrated qualification but opens one targeted exact-equivalence follow-up, `MVSTATE-REUSE1`; therefore the complete CPU optimization program is not yet closed.

## Authority boundary

CAMPAIGN-PERF-QUAL1 is a measurement/integration gate. It MUST NOT change scientific algorithms, target-data authority, replay source/split/label authority, model predictions, checkpoint selection, or GPU numerical authority. Performance telemetry, profiling, worker schedules, and the decision to open a later exact-equivalence gate are execution/documentation state.

The active CPU qualification uses the supplied MACE-MPA-0 medium checkpoint identity. The closure record is foundation-model generic and MUST remain valid for the supported MACE-MH-1 path because no foundation inference semantics are changed by this gate.

## Integrated target-data qualification

The canonical closure fixture contains 8,192 candidates, six exact neighborhood families, a 4,096-frame master selection, two repair swaps, and one same-N qualification domain. The actual chain is FEAS1 -> NEIGHBOR1 -> MVIDX1 -> MVSEL1 -> REPAIR1 -> MVQUAL1.

An untouched 0.20.225a0 PERFBASE1-era source tree is the chain control. Current execution uses the complete optimization sequence through 0.20.234a0. Exact reference, role, feasibility, sparse-index, selection, repair, and qualification digests MUST match. The current realization MAY additionally persist the NEIGHBOR1 execution-cache digest.

The qualification evidence records approximately 27.255 s for the completed control and a 4-lane current median of approximately 11.948 s, about 2.28x faster end-to-end. Timing is execution evidence only.

## Restart and memory qualification

The closure MUST retain:

- authenticated NEIGHBOR1 reuse with no second MVIDX geometry sweep;
- exact replay source-index restart reuse and exact monitor reconstruction;
- no scientific identity dependence on worker count or cache location;
- bounded resource admission under explicit campaign scopes.

The representative target chain peaks at roughly 343 MiB RSS at four lanes versus roughly 306 MiB for the old control. This retained-state increase is accepted because it remains comfortably below the qualification memory ceiling and no backpressure/memory-ceiling violation occurs.

## Reprofile decision

The gate MUST profile the new dominant target-data tail instead of assuming the previous gate order remains representative. The revision-102 profile establishes:

- MVSEL rank choice is not the primary residual selector cost; exact sparse `_select_and_update` state mutation dominates it.
- REPAIR repeats essentially the complete selected-order sparse state construction, producing 4,098 additional `_select_and_update` calls on the closure fixture and consuming several seconds before/around proposal scoring.
- This repeated state reconstruction is reconstructible execution work rather than a scientific decision.

Therefore the optimization program MUST remain open for `MVSTATE-REUSE1`.

## Acceptance

CAMPAIGN-PERF-QUAL1 passes when integrated scientific digests, restart behavior, memory ceiling, and worker scaling are qualified. Its final state is `PASS_FOLLOWUP_REQUIRED`, not a false claim of total optimization closure.

Next gate: `MVSTATE-REUSE1`.
