# Density wall-time policy amendment — 0.20.100a0

## Status

Implemented in mdstats 0.20.100a0. This amendment supersedes earlier plotting
specification language that treated scene wall time as a feasibility/admission
constraint.

## Policy

Density preparation and rendering are bounded by correctness, memory, structural
size, explicit expert operation caps, and browser/output geometry limits. Runtime
wall-time estimates are **advisory only**. A density scene must not be rejected,
truncated, or automatically timed out solely because an estimated or measured
wall time exceeds `max_wall_time_seconds`.

`max_wall_time_seconds` and `MDSTATS_MAX_WALL_TIME_SECONDS` remain accepted for
backwards compatibility and diagnostics. They record a target against which the
planner can report `wall_time_budget_exceeded`, but they do not control admission.
The cost model remains useful for choosing among otherwise feasible backends.

## Required implementation behavior

1. Phase-C global density planning records estimated preparation time but never
   rejects a backend combination for exceeding the target.
2. Hybrid direct/FFT realization records its estimated wall time but never rejects
   for exceeding the target.
3. Default operation-only limits such as `max_density_kernel_pairs` and
   `max_density_fields` are not derived from wall time. Memory-derived defaults
   and explicit caller caps remain authoritative.
4. Measured partitioned preparation, scene preparation, mesh preparation, and final
   rendering times are recorded but do not raise `GraphComplexityError`.
5. Isolated mesh workers receive no implicit timeout from the scene wall-time
   target. `worker_timeout_seconds`, when explicitly supplied by an expert caller,
   remains a separate opt-in process kill switch and is not clamped to the scene
   target.
6. CPU/thread, memory, browser geometry, mesh-face, address-space, and scientific
   correctness checks are unchanged.

## Compatibility

The existing `max_wall_time_seconds` fields and `--max-wall-time` example option
remain readable. The examples also expose the clearer `--wall-time-target` alias.
Serialized resource records continue to carry the historical field so old campaign
and plotting metadata remain parseable.
