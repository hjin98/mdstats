# N2.1/GK1 quadrature and VACF-transport implementation audit

Release target: `mdstats 0.19.1a0`  
Date: 2026-07-14

## Implemented source

- `mdstats/analysis/_quadrature.py`
- `mdstats/analysis/vacf_transport.py`

## Public API

- `VACFDiffusionResult`
- `integrate_vacf_to_diffusion()`

Both are exported from `mdstats.analysis` and the top-level `mdstats` package.
The N2.1 helper remains private.

## Numerical contract

- sampled cumulative composite trapezoidal integration;
- exact leading zero and length preservation;
- finite, one-dimensional, strictly increasing coordinate validation;
- uniform or nonuniform time grids;
- scalar Green-Kubo normalization by `1/d`;
- Cartesian component integration without an additional dimensional factor;
- canonical Angstrom^2/ps storage and derived cm^2/s conversion;
- truncation only at an existing lag boundary;
- no interpolation, extrapolation, tail fitting, or plateau selection.

## Physical-weighting guard

Accepted VACFs use either:

- package `uniform` weights, all exactly one within strict tolerance; or
- explicit equal positive weights, labeled `explicit_uniform` after validation.

Mass weighting, nonuniform explicit weighting, inconsistent uniform labels, and
unknown weighting modes are rejected.

## Provenance boundary

The Green-Kubo relation is attributed to Green (1954) and Kubo (1957). The
quadrature implementation is attributed to SciPy and its published software
reference. The weighting guard, exact stored-integrand convention,
lag-boundary truncation, immutable result schema, metadata, and refusal to
select a plateau are identified as mdstats designs.

## Focused validation

```text
tests/test_quadrature.py
tests/test_vacf_transport.py
tests/test_vacf.py
```

Coverage includes uniform and nonuniform grids, direct SciPy and analytic
oracles, component/scalar additivity, atom-count normalization, weighting
rejection, exact truncation policy, unit conversion, input immutability, and
result-identity validation.

## Documentation validation

The following paired specifications were generated, preflighted, rendered, and
visually inspected:

- `docs/specs/analysis/_quadrature_spec.{md,pdf}`;
- `docs/specs/analysis/vacf_transport_spec.{md,pdf}`.

The integrated VACF/dynamics roadmap was updated and its affected pages were
re-rendered and inspected.

## Deferred interpretation

GK2 remains responsible for explicit plateau selection and later stable-window
diagnostics. GK1 does not expose a property named `diffusion_coefficient` and
does not treat the last running value as converged.
