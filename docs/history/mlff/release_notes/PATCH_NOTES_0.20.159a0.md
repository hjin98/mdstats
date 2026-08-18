# mdstats 0.20.159a0 — GFX3D HARDEN4

This revision fixes the apparent density-realization stall reported after HARDEN3. The PAR-DENS3 scene scheduler was not deadlocked: adaptive GFX3D local-sparse fields were admitted correctly, but the direct tiled realization backend did not consume the scheduler's cooperative CPU lease. On a many-core host, one to three busy cores can therefore look like zero utilization while the CLI remains at `density_realization [0/4 fields]`.

## Gate 1 — exact lease-aware direct sparse execution

- Direct sparse tiles now use the live `DensityWorkerLease` between approved pair chunks.
- Parallel work is confined to disjoint contiguous source-row slices *inside one already-approved pair chunk*. Workers compute periodic target coordinates and packed target lookups into their canonical flattened positions.
- The floating-point accumulation remains a single stable grouped reduction over the full pair chunk in the historical pair order. Scientific output therefore does not depend on the number of workers.
- The aggregate pair count never exceeds the Phase-B `pair_chunk_size`; worker count does not multiply pair workspace.
- The direct transient-memory estimate is increased from 96 to 112 bytes/pair to include the shared mapped-index buffer retained until canonical reduction.
- A persistent per-field thread pool is created lazily and observes dynamic lease growth. When sibling fields finish, the remaining field can consume the returned CPU tokens on subsequent chunks.

## Gate 2 — scheduler and kernel observability

Density realization now reports:

- scene scheduler CPU/memory authority;
- each admitted task, backend, initial worker allocation, and declared peak memory;
- field-level admission/completion and maximum worker allocation;
- sparse direct-pair progress approximately every two seconds, including the current live worker count;
- FFT-tile progress before potentially long monolithic FFT calls;
- explicit notice that direct sparse tiles are CPU execution, while GPU use is possible only for FFT tiles selected by the approved execution plan.

This makes a long density field distinguishable from scheduler admission, memory waiting, direct CPU convolution, or FFT execution.

## Scientific/resource invariants

HARDEN4 does **not** change:

- atom selections, registration, grid shape, adaptive bandwidth, finite Gaussian support, CIC source field, support atlas, or HDR definition;
- Phase-B direct-versus-FFT tile ownership;
- pair-chunk size or canonical pair ordering;
- stable grouped floating-point reduction order;
- normalization and final mass correction;
- GPU scientific semantics.

The worker-parallel path is required to produce `np.array_equal` packed density values against the one-worker path.

## Qualification

Focused density/GFX3D regression qualification includes scheduler, PAR-DENS3/PAR-DENS6, density planning, atomic/framework density, framework dynamics, GFX3D layers, and HARDEN3 compatibility.

Measured on the supplied Na-LTA dump with the likely type map `1=Al,2=Na,3=O,4=Si` and `--stride 500` in the 3-CPU-token packaging container:

- one `density:Na` field: HARDEN3 ~4.8 s density realization; HARDEN4 ~3.8 s;
- four-density compatibility preset: HARDEN3 ~20.4 s; HARDEN4 ~16.8 s;
- the O field begins with one worker while three fields are active, then grows to three workers after the other fields complete;
- all four fields reach `density_realization [4/4 fields]` successfully.

A forced-direct synthetic case with 8,421,376 exact pairs measured ~0.675 s serial and ~0.495 s with four workers (~1.36x), and its packed density arrays were bitwise identical. No GPU speedup is claimed for this path because direct sparse tiles are CPU kernels by design.

The same four-field smoke then moves into sparse isosurface rendering; periodic component labeling/render extraction is a separate downstream hotspot and is not conflated with PAR-DENS realization in this revision.
