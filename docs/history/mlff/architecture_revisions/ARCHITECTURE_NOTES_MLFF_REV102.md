# MLFF architecture revision 102 - CAMPAIGN-PERF-QUAL1

Release: mdstats 0.20.235a0  
Date: 2026-08-17

CAMPAIGN-PERF-QUAL1 qualifies the accumulated CPU optimization program as an integrated exact-equivalence chain. It is a measurement/documentation release and does not change scientific algorithms or GPU numerical authority.

On the common 8,192-candidate/six-family target-data closure fixture, the PERFBASE1-era 0.20.225a0 control completes the FEAS1 -> MVIDX1 -> MVSEL1 -> REPAIR1 -> MVQUAL1 chain in about 27.26 s. The optimized realization through 0.20.234a0 completes it in a four-lane median of about 11.95 s (~2.28x) with exact reference, feasibility, sparse-index, selection, repair, and qualification digests. Replay restart and EVAL2/bootstrap records also reproduce exactly, and representative memory remains within the campaign ceiling.

The reprofile changes the forward optimization plan. MVSEL rank choice is no longer the dominant selector cost; exact sparse state mutation is. More importantly, REPAIR reconstructs essentially the complete selected-order state by replaying thousands of MVSEL updates, duplicating state that already existed at the selector boundary. The architecture therefore does not falsely declare CPU optimization complete.

Next gate: MVSTATE-REUSE1, an exact selector-to-repair sparse-state handoff with the old replay path retained as oracle. Final GPU qualification remains deferred.
