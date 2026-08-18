# mdstats 0.20.158a0 — GFX3D HARDEN3

This revision fixes the long-trajectory atomic-connectivity / atomic-mean-graph failure reported after GFX3D HARDEN2 and removes several scaling bottlenecks without changing connectivity cutoffs, hysteresis semantics, canonical graph identity, or periodic-density science.

## Gate 1 — minimum-image and mean-graph correctness

- General triclinic minimum-image geometry now carries integer image labels exactly through the unimodular Minkowski reduction transform. It no longer reconstructs image shifts afterward with `inv(cell)` plus rounding.
- The MIC invariant is checked in the numerically stable reduced basis. An ill-conditioned-cell regression reproducing the former failure is compared directly with ASE `find_mic`.
- Atomic mean-graph periodic averaging gains a certified single-start Fréchet path. It is accepted only inside a conservative strong-convexity ball; broad or ambiguous periodic samples retain the previous exact multi-start/weighted-medoid fallback.

## Gate 2 — connectivity execution and bounded memory

- Canonical connectivity state construction is array-oriented and transition edge differences use a linear merge over canonical sorted endpoint arrays.
- The raw canonical-state reuse cache is capped at 512 entries. Long fragmented trajectories can no longer retain millions of Python `AtomicEdgeKey` objects solely as cache keys.
- Fixed fully periodic cells reuse an exact cached cell-list search/stencil plan keyed by cell, PBC, cutoff, and cell-list options.
- LTA-style Si-O / Al-O / mobile-ion-O cutoff registries are recognized as a shared-species star and evaluated by one exact broad neighbor request with pair-specific filtering instead of repeated MIC searches per species pair.

## Gate 3 — one-pass atomic/framework connectivity

- The HARDEN2 trajectory-wide cross-pass neighbor-geometry cache is removed from the LTA provider.
- When both atomic connectivity and framework topology are requested, the broader hysteretic atomic graph is computed once. The framework graph is then projected exactly from the source states when its scope/pairs/cutoffs are a strict identical subset.
- Real-trajectory qualification confirms identical framework state digests, frame-state IDs, and transitions versus a separate direct framework connectivity computation.
- The existing frame-threaded candidate path remains available internally but is not selected automatically for this workload: measured fixed-cell LTA runs were slower than the optimized serial cell-list/star fold because candidate materialization and Python/GIL overhead outweigh thread-level gains.

## Qualification

Focused regression suite: **191 passed**.

A cold 400-frame full-connectivity comparison on the supplied Na-LTA trajectory, using the same likely type map (`1=Al,2=Na,3=O,4=Si`) and the same scientific connectivity definition, measured:

- `0.20.157a0`: ~6.59 s, 138 states.
- `0.20.158a0`: ~1.59 s, 138 states.
- Canonical connectivity identity SHA-256 was identical: `fab68c78b8eb3779cf3e6ff857245f4f209f257178c4b910f538fd0bbd8bd35a`.

A full 10,001-frame `framework + connectivity + trajectory:Na` GFX3D run on the supplied dump completed successfully:

- input: ~9.34 s;
- atomic connectivity: resolved 2,912 states by ~41.5 s of preparation;
- exact framework projection: ~1.3 s, 15 framework states;
- framework topology: 15 topologies;
- atomic mean graph completed without the previous minimum-image reconstruction exception;
- source preparation completed by ~102.2 s, of which framework registration was the new dominant stage (~52 s);
- final self-contained HTML: ~17.3 MiB;
- exit status: 0.

The full run reached a maximum RSS of ~2.85 GiB, largely during later framework registration/render preparation. That stage is now the principal remaining long-trajectory GFX3D optimization target; it is separate from the repaired connectivity/MIC failure.
