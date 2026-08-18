# mdstats 0.20.141a0 patch notes

## PAR-DENS1 / PAR-DENS2: execution-faithful density calibration and global scheduler

- Close the previously missing PAR-DENS1 prerequisite with execution-faithful runtime calibration for irregular destination indexing, `bincount` and `np.add.at` direct reductions, packed support-region work, and worker-aware `scipy.fft` overlap-add cost classes.
- Advance the density time model to `mdstats.density-time-model.v3`, retaining synthetic/input-independent calibration while persisting thread count, dtype, tile/kernel/padded shapes, occupancy, contribution counts, temporary memory, and FFT backend.
- Price direct reduction conservatively from the slower measured `bincount`/`np.add.at` path and derive hybrid direct-vs-FFT cross-over costs from the calibrated rates. Wall-time estimates remain advisory and never become feasibility gates.
- Implement `DensitySceneScheduler` with one LD10 affinity/cgroup/scheduler-aware CPU/RAM authority, aggregate peak-memory admission, minimum/preferred worker leases, deterministic water-filling and CPU return, parent/child ownership, deterministic result collation, and bounded thread/process helpers.
- Integrate PAR-DENS2 into framework-density scene realization without enabling PAR-DENS3 concurrency yet: all field task contracts are validated transactionally and existing serial realization runs under one scheduler-owned scene lease.
- Keep the complete scene memory ceiling visible to nested planners while scheduler admission owns aggregate task peaks, preventing resource scheduling from silently changing approved grid or backend feasibility.
- Advance density scene plans to `mdstats.density-scene-plan.v2`: scientific approval identity is worker/backend/timing neutral, while `execution_plan_id` retains complete resource/backend evidence. Historical v1 plans preserve their original resource-sensitive digest semantics.
- Qualify worker-count invariance on the supplied 10,001-frame 300 K Na-LTA source using a bounded 21-frame, 64^3 Na-density smoke: one- and four-thread fields are bit-identical and share the same scientific approval ID.
- Preserve the existing PAR-DENS0 scientific density/spread semantics. PAR-DENS3 remains the next gate and owns actual concurrent density planning/realization.
- Canonicalize unavailable spread-convergence diagnostic sentinels as JSON `null`/Python `None` instead of non-finite `NaN` metadata; this is serialization-only and leaves the underlying spread and density numerics unchanged.
