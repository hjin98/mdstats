# mdstats 0.20.160a0 — GFX3D HARDEN5

This revision adds continuous, field-scoped observability to long PAR-DENS density preparation. HARDEN4 already reported scheduler admission and direct-pair convolution progress, but a field could still spend substantial time before convolution while constructing its CIC source, Gaussian stencil/routing, and exact support atlas. During that interval the CLI could remain at `density_scheduler [0/4 fields]` even though useful work was in progress.

## Gate 1 — sparse-field preparation progress

Each local-sparse density field now reports a five-step pre-convolution pipeline:

1. aggregate periodic CIC source;
2. resolve the finite Gaussian stencil;
3. pack positive CIC source blocks;
4. resolve block routing;
5. construct the exact support atlas.

Messages are field-scoped by stable keys such as `atomic-density-2`, so concurrently executing fields remain distinguishable.

## Gate 2 — exact support-atlas progress

`build_density_support_atlas()` now accepts an optional progress port and field key. It reports:

- selected dilation backend (`bitset` or `fft`);
- source block count and stencil-offset count;
- source blocks completed/total, throttled to approximately two-second updates for long fields;
- live worker count;
- a finalization stage while routed support blocks are merged and the CSR lookup is built;
- final target block/node counts and atlas wall time.

The progress API is execution-only and does not participate in scientific identity, cache identity, or resource planning.

## Gate 3 — scheduler heartbeat

The PAR-DENS scene scheduler no longer blocks indefinitely in `wait(FIRST_COMPLETED)` without user-visible output. While no field has completed, it emits a heartbeat every five seconds showing:

- completed/total fields;
- active and pending field counts;
- active task IDs and their current worker allocations.

This heartbeat is deliberately independent of low-level field progress, so temporary silence inside a native or memory-bound kernel is still distinguishable from a scheduler deadlock.

## Qualification

Focused density/GFX3D qualification: 81 tests passed (60 density-path + 21 GFX3D CLI/hardening).

A real Na-LTA `--stride 500` four-density smoke reached density completion and showed concurrent field progress such as:

```text
sparse_field_preparation [4/5 steps]: atomic-density-2: routing resolved; constructing exact support atlas
density_support_atlas [312/800 source blocks]: atomic-density-2: dilating exact support; backend=fft; workers=1
density_scheduler [0/4 fields]: density tasks still running; active=3; pending=1; allocations=[atomic-density-1:1w, atomic-density-2:1w, atomic-density-3:1w]
hybrid_direct_realization [84300125/181328875 pairs]: atomic-density-2: CPU direct sparse convolution; workers=3
density_realization [4/4 fields]: completed parallel density field realization
```

No scientific density numerics, backend selection, Phase-B plan ownership, normalization, or rendering semantics are changed in HARDEN5.
