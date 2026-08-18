# G3/GK4 VACF-to-MSD reconstruction implementation audit

Release target: `mdstats 0.19.5a0`  
Date: 2026-07-15

## Implemented source

- `mdstats/analysis/vacf_transport.py`

## Public API

- `VACFMSDResult`
- `reconstruct_msd_from_vacf()`

Both are exported from `mdstats.analysis` and the top-level `mdstats` package.

## Numerical contract

- physical equal-positive per-particle VACF normalization;
- scalar total or one Cartesian directional reconstruction;
- two cumulative composite trapezoidal moments;
- `MSD(t) = 2 * [t I0(t) - I1(t)]`;
- $O(T)$ work and $O(T)$ output storage after VACF construction;
- optional truncation at an existing lag boundary only;
- no interpolation, smoothing, tail fit, or automatic direct-MSD acceptance.

## Physical-weighting guard

Accepted VACFs use package-uniform weights or explicit equal positive weights.
Mass weighting, nonuniform explicit weighting, malformed uniform labels, and
unknown modes are rejected.

## Provenance boundary

Einstein supplies the displacement representation of diffusion; Green and Kubo
supply the time-correlation transport framework; Helfand supplies the equivalent
displacement-moment transport lineage; SciPy supplies the cumulative trapezoid
implementation. The two-moment sampled rearrangement, immutable result schema,
validation identities, truncation policy, metadata, and diagnostic-only
interpretation are mdstats designs.

## Focused validation

```text
tests/test_vacf_msd.py
tests/test_vacf_transport.py
tests/test_quadrature.py
tests/test_vacf.py
tests/test_msd.py
```

Coverage includes exact ballistic motion, analytic exponential correlation,
nonuniform-grid direct oracles, scalar/component additivity, direct MSD
agreement, physical-weight rejection, truncation, input immutability, public
exports, and result identity validation.

## Documentation validation

The paired specification

- `docs/specs/analysis/vacf_msd_reconstruction_spec.{md,pdf}`

and the integrated VACF/dynamics roadmap are regenerated, preflighted, rendered,
and visually inspected for the release.

## Interpretation boundary

Direct position-based MSD remains primary. Finite-record VACF and MSD estimates
are not forced to agree, and GK4 does not declare either estimator correct.
