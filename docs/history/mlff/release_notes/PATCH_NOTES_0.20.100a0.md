# mdstats 0.20.100a0 patch notes

This plotting-policy hotfix removes wall time as a hard density-scene bound.

## Changed

- Phase-C density planning no longer rejects a scene because its estimated preparation wall time exceeds `max_density_wall_time_seconds`.
- Hybrid direct/FFT planning no longer rejects because its estimated realization time exceeds `max_wall_time_seconds`.
- Partitioned preparation, full scene preparation, mesh rendering, and final scene assembly no longer raise solely because measured/estimated wall time exceeds the configured target.
- Default `max_density_kernel_pairs` and `max_density_fields` are no longer derived from wall time.
- Isolated mesh workers no longer inherit an implicit scene-derived timeout. An explicitly supplied `worker_timeout_seconds` remains opt-in.
- Wall-time estimates and exceedance booleans remain in metadata for diagnostics and backend cost selection.

## Unchanged hard bounds

Memory, threads, address-space-safe structural counts, browser mesh/output budgets, explicit expert operation caps, and scientific correctness checks remain enforced.

## Compatibility

`max_wall_time_seconds`, `MDSTATS_MAX_WALL_TIME_SECONDS`, and `--max-wall-time` remain accepted. The LTA density example also accepts `--wall-time-target`. The MLFF campaign compatibility token remains 0.20.99a0.
