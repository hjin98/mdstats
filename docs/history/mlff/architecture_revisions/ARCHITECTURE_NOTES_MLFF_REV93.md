# MLFF Architecture Revision 93

**Gate:** `PARCORE1`  
**Release:** `mdstats 0.20.226a0`  
**Authority:** runtime execution optimization under exact scientific equivalence

Revision 93 implements the shared deterministic CPU scheduling substrate that follows the PERFBASE1 measurement gate. The new `mdstats.training_data.work_queue` module provides bounded ready/in-flight/completed work, work-conserving dispatch, deterministic ordered reducers, resource-scoped native-thread quarantine, task-identity errors, memory-weighted admission/backpressure, persistent memory reservations, heartbeat telemetry, and locality metadata. `StageResourceScope` now carries an execution-only RAM budget.

FEAS1 is the first migrated consumer. Its former private `ThreadPoolExecutor` coordinator is replaced by `DeterministicWorkQueue`, while feature scaling, cKDTree neighborhood mathematics, one-native-worker-per-task policy under outer parallelism, witness-block decomposition, and canonical FP64 reduction order are unchanged. The queue may keep up to twice the worker-count futures submitted so executing lanes can pull admitted work immediately; simultaneously executing Python workers remain bounded by `StageResourceScope.python_workers`.

The active qualification uses the supplied MACE-MPA-0 medium checkpoint identity inherited from PERFBASE1. PARCORE1 contains no foundation-model-specific behavior and applies unchanged to MACE-MH-1 campaigns. No MACE inference, training, evaluation, target-selection, or GPU authority is changed.

The exact FEAS1 scientific digest remains `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613` across all tested worker schedules. On the same cgroup-limited cloud host, the final paired two-repeat three-worker result is about 0.83 s for PARCORE1 versus about 0.94 s for the untouched `0.20.225a0` implementation, with assigned-lane occupancy about 0.66 versus 0.64. The PARCORE1 result is also consistent with the frozen PERFBASE1 median near 0.85 s. Queue contract tests verify three-lane saturation, deterministic out-of-order reduction, RAM backpressure/release, and deterministic exception identity.

Canonical evidence:

- `benchmarks/mlff_parcore1_feas1_cloud_cpu_mpa0_2026-08-17.json`
- `benchmarks/mlff_parcore1_feas1_cloud_cpu_mpa0_2026-08-17.md`
- `release/qualification_logs/MLFF_PARCORE1_QUALIFICATION_0.20.226a0.json`

`NEIGHBOR1` is the next gate. It will move exact FEAS1/MVIDX1 neighborhood production onto the shared queue and persist canonical streamed CSR for reuse.
