# S2 Fixed-Cell Verlet Cache Implementation Audit

## Release

```text
Package: mdstats
Version: 0.14.0a2
Stage: S2 - fixed-cell Verlet candidate caching
```

## Implemented source boundary

- `mdstats/analysis/_verlet_cache.py` owns request digests, immutable candidate caches, fixed-cell validity, current MIC reevaluation, and statistics.
- `mdstats/analysis/_cell_list.py` remains the exact rebuild backend.
- `mdstats/analysis/_neighbors.py` retains dense and stateless cell-list paths and records `VERLET_CACHE` only as session result provenance.
- `mdstats/analysis/atomic_connectivity.py` provides explicit opt-in session integration and one-pass nested thresholds.

## Invariants reviewed

1. Candidate construction uses `physical_cutoff + skin`.
2. The enlarged list radius is validated against the unique-image safety bound.
3. Result filtering uses the strict physical cutoff.
4. Current MIC geometry and original-basis image shifts are recomputed on every frame.
5. Equality at `2*d_max == skin - tolerance` rebuilds.
6. Any cell-matrix change rebuilds in S2.
7. Request changes create separate caches.
8. Cache and result arrays are defensive and read-only.
9. Bond-history state is not stored in the candidate cache.
10. No S3 deformation-aware reuse or S4 automatic policy is active.

## Test matrix

The focused matrix covers solid-like and diffusive motion, periodic boundary crossings, noncontiguous frame order, entering and omitted pairs, exact rebuild thresholds, request invalidation, cell changes, unsafe list radii, randomized triclinic systems, immutable cache arrays, and stateless-facade guards.

Atomic integration tests verify distance, hysteretic, and reference definitions against uncached canonical state digests.

## Result

The S2 acceptance gate passed. The complete regression suite contains 259 passing tests with 24 expected warnings inherited from sparse-analysis and visualization fixtures.
