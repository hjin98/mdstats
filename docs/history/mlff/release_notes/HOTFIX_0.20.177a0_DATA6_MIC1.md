# mdstats 0.20.177a0 DATA6-MIC1 hotfix

## Scope

This hotfix repairs a failure in DATA6 universal structural-feature finalization:

```text
InvalidCellGeometryError:
Reduced-basis minimum-image lattice bookkeeping became inconsistent.
```

No DATA6 selection policy, structural-feature definition, model policy, or
scientific threshold is changed.

## Root cause

`minimum_image_vectors()` is the vectors/distances-only MIC API used by DATA6
local-structure features. Although its public contract explicitly did not require
integer image shifts, it delegated to `_cached_general_find_mic()`, which also
reconstructed and validated integer reduced-basis image labels. A displacement
lying within floating-point noise of an integer reduced-lattice plane could be
classified on opposite sides of `floor()` because label reconstruction used
`vectors @ inv(reduced)` while ASE `wrap_positions()` uses a linear solve. The
result was a spurious whole-cell label mismatch and a false
`InvalidCellGeometryError` even though the MIC vector itself was valid.

## Repair

- Factor the cached ASE-equivalent geometric MIC search from image-label
  reconstruction.
- Route `minimum_image_vectors()` through a genuinely label-free path.
- For image-bearing `minimum_image_geometry()`, derive reduced fractional
  coordinates with the same `np.linalg.solve(reduced.T, vectors.T).T` convention
  used by ASE `wrap_positions()` before applying integer wrapping logic.
- Preserve the strict reduced-basis reconstruction check for callers that
  actually request image shifts.
- Add regression coverage using an LTA-like primitive cell and a displacement
  on a floating-point reduced-lattice boundary, including the complete
  `compute_local_structure_features()` DATA6 path.

## Qualification

Focused neighbor, local-structure, GFX3D-HARDEN3, and universal structural
selection tests pass under the supplied ASE 3.29.0 dependency source. A
100,000-vector LTA-like stress check, with 20% of vectors deliberately placed
within ulps of integer lattice planes, matched ASE MIC vectors exactly and MIC
distances to floating-point precision; image-shift reconstruction residuals
remained below `3e-13` angstrom.
