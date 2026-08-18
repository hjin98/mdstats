# mdstats 0.20.161a0 — GFX3D HARDEN6

This revision fixes the real cause of the apparent PAR-DENS stall that could occur immediately after density tasks were admitted, and removes a second major source of duplicated density work.

## Gate 1 — eliminate production-time recalibration

The `density_scheduler_task: started ...` message was emitted before the scheduled field entered its scientific realization function. Inside that function, low-level density helpers called `resolve_density_resource_limits()` again under the field's current worker lease. Because PAR-DENS1 calibration is cached by worker count, a scene that admitted fields with 9, 9, and 10 workers could launch fresh synthetic FFT/BLAS calibration for those worker counts.

Those calibrations use SciPy FFT plus `threadpoolctl.threadpool_limits()`. Native thread limits are process-global, so running several calibrations concurrently from field threads is both redundant and a poor concurrency boundary. The calibration also happened before HARDEN5's first field-scoped progress event, producing exactly the observed symptom: three `started` lines, almost no visible utilization, and no field progress.

HARDEN6 makes the scene-resolved `DensityTimeModel` a context-local execution authority, analogous to the existing scene resource budget. The scheduler already copies context into each field worker; therefore every nested density helper now inherits the same calibrated model even while its live worker lease changes from 9 to 28 workers. Worker allocation remains an execution detail and no longer triggers scientific/runtime-model recalibration.

A regression monkeypatches the calibrator to fail and executes nested resource resolution inside a scheduler worker. The scheduled task must complete using the inherited model without invoking calibration.

## Gate 2 — reuse Phase-B sparse execution artifacts

Phase B already constructs the exact objects required to approve a `local_sparse` field:

- aggregated periodic CIC source;
- finite Gaussian stencil support;
- packed positive CIC source;
- periodic block routing;
- exact support atlas;
- hybrid tile execution plan.

Before HARDEN6, realization received only the compact resolved numerical plan and hybrid tile plan. It then reconstructed CIC/stencil/source/routing/atlas from the raw samples. The expensive support-atlas work was therefore performed twice for every sparse atomic density field.

HARDEN6 carries the exact Phase-B sparse objects through an execution-only sidecar and hands them directly to atomic-field realization. The approved hybrid plan still validates the objects before numerical execution; scientific/cache identity remains owned by the serialized Phase-B plan, not by the sidecar. Sparse candidate artifacts for AUTO fields whose final approved backend is not `local_sparse` are discarded before scheduling.

The CLI now reaches direct convolution immediately after task admission with messages such as:

```text
density_scheduler_task [0/4 fields]: started atomic-density-2 ...
field_realization [1/1 fields]: resolving samples and numerical plan
sparse_field_preparation [5/5 steps]: atomic-density-2: reusing exact Phase-B CIC/stencil/routing/support atlas; no duplicate sparse planning
hybrid_sparse_realization: atomic-density-2: realizing ... direct tile(s)
```

## Gate 3 — remove per-source-block resource resolution

FFT support-atlas dilation previously called `resolve_density_resource_limits()` once per source block solely to retrieve the density time model used for CPU/GPU cost comparison. An atlas can contain hundreds of source blocks. HARDEN6 resolves the scene resource/time model once in `build_density_support_atlas()` and passes the scalar FFT rate into each block dilation.

This does not change FFT dilation, the integer-convolution certificate, GPU eligibility, or support identity.

## Real Na-LTA smoke

Input: supplied `dump.prod.Na_lta_300K.old(2).lammpstrj`, `--stride 500`, type map `1=Al,2=Na,3=O,4=Si`, four density fields, four CPU tokens.

Observed preparation timeline:

```text
density_planning started                      ~1.4 s
density_realization / scheduler started      ~11.6 s
first field execution progress               ~11.6 s
Al density completed                         ~15.1 s
Na density completed                         ~16.1 s
Si density completed                         ~18.4 s
O density completed                          ~24.1 s
density_realization 4/4                      ~24.1 s
registered source-scene preparation complete ~24.5 s
```

There is no longer a silent interval between scheduler admission and field execution.

Representative exact direct-pair work remains large:

- Al: 45,393,032 pairs;
- Na: 45,240,660 pairs;
- Si: 45,338,370 pairs;
- O: 181,328,875 pairs.

The adaptive framework-species fields also remain extremely fine (approximately 800-1076 logical nodes per dimension, with Gaussian bandwidths around 0.035-0.047 Å). This is now genuine scientific execution cost, not hidden scheduler/calibration overhead.

## Remaining optimization opportunities

HARDEN6 intentionally does not change density science. The next genuine hotspots are:

1. Phase-B planning remains serial across independent species. Safe parallel planning requires explicit aggregate memory admission and native FFT-thread coordination rather than a raw `ThreadPoolExecutor`.
2. FFT support-atlas dilation recomputes the binary-kernel spectrum for each source block. A future exact implementation can cache spectra by padded shape, but the retained spectrum memory must be included in the Phase-B memory contract.
3. The historical four-species LTA preset computes Si, Al, O, and mobile-ion density. Nearly static framework species generate very small adaptive bandwidths and huge logical grids. An opt-in visualization bandwidth floor or mobile-ion-only preset would dramatically reduce cost, but would change requested density semantics and is therefore not silently introduced here.
4. After preparation, sparse isosurface connected-component labeling remains a separate rendering hotspot.

## Qualification

Focused qualification: **154 tests passed** across runtime resources, PAR-DENS scheduling, support atlas, tiled realization, atomic density, framework dynamics, GFX3D CLI/contracts/dependencies/rendering, and previous hardening regressions.

No density normalization, grid/bandwidth policy, scientific backend selection, direct-pair ordering, topology semantics, or rendering semantics are changed by HARDEN6.
