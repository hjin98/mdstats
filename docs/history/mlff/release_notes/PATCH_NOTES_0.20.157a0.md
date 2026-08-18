# mdstats 0.20.157a0 — GFX3D HARDEN2

This revision hardens and accelerates the existing universal 3-D framework / connectivity / trajectory / density path without changing the scientific definitions of those layers or the historical `lta-mixed-alkali-density` preset.

## Gate 1 — failure-path and sparse-render correctness

- The raw LTA source is now single-flight for both success and failure. A failed preparation is latched and reused by all product requests instead of being retried by each waiting dependency future.
- CLI errors preserve the causal exception chain, so the underlying preparation failure is visible rather than being reduced to `Failed to resolve GFX3D dependency ...`.
- Packed sparse atomic-density fields are rendered through the existing sparse mesh/node-cloud pipeline rather than a dense `.values` path.
- Sparse-shell face limits are treated as visual targets under the scene-level browser budget, avoiding an unnecessary expensive simplifier while retaining the aggregate browser safety gate.

## Gate 2 — input and connectivity scaling

- Positive LAMMPS `start` / `stop` / `stride` selection is applied during streaming file scan. Discarded atom tables are not tokenized/materialized, while the exact source frame count is retained.
- The framework-only and full atomic-connectivity passes share one exact `AtomicConnectivityGeometryCache`, eliminating repeated Si/Al–O pair-geometry construction without changing hysteresis or connectivity states.
- GFX3D now reports framework calibration, framework connectivity, topology construction, full atomic connectivity, and registered scene/density stages during preparation.

## Gate 3 — density planning and topology diagnostics

- Phase-B adaptive density numerics are retained in a compact immutable `AtomicDensityResolvedPlan` and consumed by realization rather than being resolved a second time.
- The plan intentionally does not retain duplicate coordinate samples, preserving the existing memory-planning model.
- The LTA source warns when mapped framework species show implausible tetrahedral-neighbor calibration or when the topology catalog is pathologically fragmented. These warnings are diagnostic: mdstats does not guess or rewrite a user-supplied type map.

## Qualification

Focused tests: **187 passed** across LAMMPS I/O, GFX3D dependency execution/CLI/rendering, framework dynamics/topology/visualization, sparse meshes, atomic density, and density preprocessing.

On the supplied 10,001-frame (~183 MiB) Na-LTA dump with `stride=500`:

- 0.20.156a0 isolated LAMMPS read: ~9.17 s, ~1.63 GiB peak RSS.
- 0.20.157a0 isolated LAMMPS read: ~3.03 s, ~253 MiB peak RSS.
- Both return the same 21 selected frames with `source_frame_count=10001`.
- A four-layer `framework + connectivity + trajectory:Na + density:Na` smoke completed successfully and wrote a ~22.1 MiB self-contained HTML file; the Na density used the packed sparse backend and rendered without the former `.values` failure.

The historical all-species density preset remains intentionally expensive for nearly static Si/Al/O populations because adaptive smearing can demand very fine logical sparse grids. For routine transport visualization, prefer explicit mobile-ion density layers such as `--layer density:Na`.

## Supplied trajectory type-map diagnostic

Geometry of the supplied `dump.prod.Na_lta_300K.old(2).lammpstrj` strongly indicates `type 2 = Na`, `type 3 = O`, `type 4 = Si-like tetrahedral sites`, and `type 1 = Al-like tetrahedral sites`, i.e. the likely map is:

```text
1=Al,2=Na,3=O,4=Si
```

The trajectory still triggers an Al tetrahedral-neighbor / topology-fragmentation warning under that mapping, so its framework integrity/cutoff history should be treated as a separate scientific diagnostic rather than hidden as a plotting performance problem.
