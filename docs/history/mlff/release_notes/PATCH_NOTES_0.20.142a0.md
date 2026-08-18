# mdstats 0.20.142a0 patch notes

## PAR-DENS3: parallel density planning and realization

- Execute independent atomic and framework density fields concurrently through the single PAR-DENS2 `DensitySceneScheduler`; aggregate retained/transient memory and minimum CPU demand remain hard admission constraints, results are collated in deterministic construction order, and CPUs released by short fields are returned to surviving fields.
- Bind every scheduled field to a live worker lease so chunked sparse kernels and FFTs can observe dynamic CPU reallocation without changing scientific results. Nested density APIs retain the scene memory ceiling while the scheduler remains the sole aggregate resource authority.
- Parallelize support-atlas/source-block construction over bounded independent source-block groups. Before field realization exists, Phase-B planning uses the global LD10 CPU/RAM ceiling; inside a scheduled task it automatically uses the task lease and declared transient-memory slack.
- Partition target-owned direct sparse realization by destination block. Each worker owns a private target accumulator and writes a disjoint packed output range, eliminating shared-output contention while preserving canonical per-block reduction order.
- Replace repeated hot global `np.add.at` scatter in hybrid realization with stable destination grouping plus compiled segmented reduction where practical.
- Standardize dense, tiled, and support-dilation FFT execution on `scipy.fft` worker semantics and source worker counts from the live scheduler allocation rather than giving every field the full scene thread count.
- Advance `mdstats.density-scene-plan` to v3. New scientific approval IDs exclude sparse storage geometry, executor/tile choices, hybrid plan IDs, FFT worker counts, cache hits, calibrated timing, and memory/work decomposition; complete execution evidence remains in `execution_plan_id`. Historical v1 and v2 plans retain their original approval semantics and round-trip without reinterpretation.
- Add PAR-DENS3 acceptance coverage comparing serial/parallel scalar fields, integrated measure, periodic packed support, HDR thresholds, and sparse meshes under multiple worker counts.
- On the supplied 300 K Na-LTA source (SHA-256 `81c86cc40f5a11031f80817213eb558c02348494d1c6cad9b4775a5bc3c9f9cd`), a 101-frame stride-100 sparse 64^3 Na/Si/O qualification produced three concurrent fields at four threads, `max |Delta rho| = 0` for every field, identical content/scientific IDs and HDR thresholds, and a measured 1.109x scene-preparation speedup over one thread in the qualification environment.
- PAR-DENS0 scientific density/spread semantics remain unchanged. PAR-DENS4 is the next gate.
