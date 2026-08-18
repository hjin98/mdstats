# mdstats 0.20.143a0 patch notes

## PAR-DENS4: parallel trajectory preprocessing and geometry reuse

- Split hysteretic connectivity into a frame-local geometric candidate phase and an authoritative deterministic hysteresis fold. `parallel_frame_workers` enables bounded candidate preparation without changing state/transition identity.
- Add `AtomicConnectivityGeometryCache`, an execution-only exact-request cache that reuses compatible periodic neighbor geometry across framework-only and broader atomic-connectivity passes. Cache state is explicitly excluded from scientific identity.
- Parallelize independent framework graph reconstruction/lifting over scene frames under PAR-DENS2 scheduler leases, then validate graph keys and residual winding deterministically in frame order.
- Parallelize independent periodic atomic-mean calculations while preserving authoritative floating occupancy accumulation order.
- Hoist frame-to-connectivity-state lookup and framework geometry caches out of partitioned topology-category loops. Independent category scenes now share the global CPU/RAM scheduler and reusable geometry instead of repeating trajectory-wide work.
- Keep nested numerical/resource ownership single-authority: nested preprocessing reuses the active scheduler lease instead of creating another unconstrained worker pool.
- Advance the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v15` for the new preprocessing provenance.

## Qualification

The supplied 300 K Na-LTA MLFF dump (SHA-256 `81c86cc40f5a11031f80817213eb558c02348494d1c6cad9b4775a5bc3c9f9cd`, 10,001 frames x 168 atoms) was sampled at stride 100 (101 frames).

- Serial and four-worker hysteretic connectivity produced identical frame-state IDs, state digests, and transition records (94 observed states in this bounded sample).
- A shared neighbor-geometry cache populated by framework-only connectivity gave 202 exact cache hits when the broader framework+Na-O connectivity was evaluated. The warm full pass measured 1.024 s versus 1.730 s cold in the qualification environment, approximately 1.689x faster, with identical scientific connectivity.
- Four-worker geometric candidate generation measured slower than serial for this small dense 168-atom/frame workload because task/thread overhead exceeds the per-frame kernel cost. This is recorded as a granularity result, not hidden; PAR-DENS4 exposes bounded parallelism but does not claim it is always profitable.
- Density/framework/connectivity regression chunks covering the complete relevant surface pass; the only skip is the existing optional `mdstats[interactive]` mesh-simplification dependency.

PAR-DENS4 is closed. PAR-DENS5 (optional GPU density execution under an explicit VRAM budget) is the next gate.
