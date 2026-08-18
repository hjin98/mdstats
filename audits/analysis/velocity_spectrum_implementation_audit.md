# VS1 velocity-spectrum implementation audit

Release target: `mdstats 0.19.0a0`  
Date: 2026-07-14

## Implemented source

- `mdstats/analysis/_spectral.py`
- `mdstats/analysis/_spectral_units.py`
- `mdstats/analysis/velocity_spectrum.py`

## Public API

- `VelocitySpectrumResult`
- `compute_vacf_spectrum()`

Both are exported from `mdstats.analysis` and the top-level `mdstats` package.

## Numerical contract

- Hermitian two-sided reconstruction from positive-lag VACF data;
- `scipy.fft.rfft` transform;
- one-sided density scaling;
- canonical THz frequency axis;
- explicit raw/per-weight normalization;
- explicit reported/biased finite-origin weighting;
- centered half-Hann and half-Tukey lag tapers;
- zero padding through `scipy.fft.next_fast_len`;
- preservation of material negative lobes by default.

## Provenance boundary

Borrowed theory is explicitly attributed to Wiener, Khintchine, Harris, and
Rahman. SciPy is cited as the numerical software dependency. Tensor layout,
normalization switches, metadata, negative policies, and validation identities
are labeled as mdstats designs.

## Focused tests

```text
tests/test_spectral.py
tests/test_velocity_spectrum.py
tests/test_vacf.py
```

The optimized transform is tested against an independent direct DFT oracle.
Tensor Hermiticity, one-sided spectral area, per-atom reconstruction, unit
axes, negative policies, and invalid inputs are covered.

## Deferred roadmap units

- Green-Kubo quadrature and VACF diffusion;
- discrete spectral-bin utility and VDOS normalization;
- plotting;
- direct Welch estimator and atom blocking.
