# mdstats 0.20.226a0 patch notes

## PARCORE1 shared deterministic CPU scheduler

This release implements `PARCORE1`, the first runtime optimization gate after PERFBASE1. It introduces `mdstats.training_data.work_queue.DeterministicWorkQueue` as the reusable bounded, work-conserving scheduler for CPU-heavy independent MLFF work and migrates FEAS1 onto it.

The queue integrates `StageResourceScope` CPU/RAM budgets, bounded ready/submitted/completed work, deterministic ordered reducers, task-identity failures, memory-weighted admission and explicit reservations, backpressure counters, heartbeat snapshots, and locality metadata for future NUMA execution. Campaign-owned scopes apply native BLAS/OpenMP quarantine once at queue scope; FEAS1 cKDTree calls remain single-native-worker tasks whenever the outer queue can populate multiple lanes.

FEAS1 retains exactly the prior scientific decomposition and canonical FP64 witness reduction order. Qualification preserves scientific digest `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613` at every worker schedule. In the final same-host paired two-repeat comparison, three-worker PARCORE1 completes in about 0.83 s median versus about 0.94 s for the untouched 0.20.225a0 implementation, with assigned-lane occupancy about 0.66 versus 0.64; the PARCORE1 result also matches the frozen PERFBASE1 scale. The common scheduler therefore introduces no measured full-budget throughput regression.

The active performance qualification still binds the supplied MACE-MPA-0 medium checkpoint, but PARCORE1 is model-agnostic and preserves full MACE-MH-1 support. No foundation-model inference, target-data scientific definition, training/evaluation policy, or GPU authority changes.

`NEIGHBOR1` is the next optimization gate.
