# mdstats 0.20.227a0 patch notes

## NEIGHBOR1 shared exact FEAS1/MVIDX neighborhood engine

This release implements `NEIGHBOR1`. `ExactNeighborhoodEngine` now owns the frozen TARGET-DATA2B exact cKDTree semantics. FEAS1 uses that engine and, during its unchanged canonical support/capacity reduction, streams exact witness->candidate edges into compact `uint64`/`uint32` CSR. Ragged neighborhood objects are released after canonical block reduction.

The forward graph is persisted as an authenticated, content-addressed execution cache whose scientific identity excludes worker count, query-block size, and queue controls. Campaign restart independently validates/reuses the cache. Missing, stale, or corrupt cache state is rebuilt once through the same global PARCORE1 engine. Final CSR allocation is admitted against the stage RAM budget before materialization.

MVIDX1 now adopts this authenticated forward CSR and performs no second geometric sweep on a cache hit. Its prior cKDTree/query-ball implementation has been removed; existing sparse inversion/obligation logic remains unchanged for `MVIDX-REUSE1`.

The PERFBASE1 FEAS1 digest remains `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613`, and MVIDX1 remains `e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c`. The 3,194,880-edge forward cache is invariant at digest `0220c89084fe957e85eb1e1c87a581eaa44869f11cb98bee7f7bd8cdafd3d74e`. Final cloud CPU evidence shows roughly 2.68x lower three-worker FEAS1->MVIDX1 wall time than untouched 0.20.226a0.

Active qualification remains the supplied MACE-MPA-0 medium checkpoint, while the engine/cache contracts remain fully model-generic for MACE-MH-1. No training/evaluation/GPU authority changes. `MVIDX-REUSE1` is next.
