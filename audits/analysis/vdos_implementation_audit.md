# N1.6/VS3 spectral-bin and VDOS implementation audit

Release target: `mdstats 0.19.2a0`  
Date: 2026-07-15

## Implemented source

- `mdstats/analysis/_spectral.py`: `spectral_bin_integral()`;
- `mdstats/analysis/velocity_spectrum.py`: `VDOSResult` and `compute_vdos()`.

## Public API

- `VDOSResult`;
- `compute_vdos()`.

Both are exported from `mdstats.analysis` and the top-level `mdstats` package.
The spectral-bin helper remains private.

## Numerical contract

- uniform one-sided FFT-bin measure `df * sum(P_m)`;
- no trapezoidal endpoint half-weights;
- exact existing-bin low-frequency cropping without interpolation;
- one scalar normalization factor for total, Cartesian, and per-atom projections;
- explicit unit-area, degrees-of-freedom, or no-normalization modes;
- explicit positive degrees-of-freedom target with no constraint inference;
- roundoff-only negative clipping and material-negative rejection.

## Provenance boundary

Velocity-correlation spectra are attributed to Rahman's molecular-dynamics
work. Lin, Blanco, and Goddard are cited only as related VACF-derived DOS/2PT
background; this release does not implement 2PT. The discrete bin measure,
normalization modes, threshold policy, negative-value policy, result schema,
and terminology safeguards are identified as mdstats designs.

## Focused validation

```text
tests/test_spectral.py
tests/test_velocity_spectrum.py
tests/test_vdos.py
```

Coverage includes multidimensional bin sums, nonzero-start uniform grids,
trapezoidal-counterexample tests, unit-area and explicit-DOF targets, per-atom
projection scaling, zero-padding invariance, low-frequency cropping, negative
policies, input immutability, result validation, and public imports.
