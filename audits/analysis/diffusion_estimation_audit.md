# G2 diffusion estimation implementation audit

Release target: `mdstats 0.19.4a0`  
Date: 2026-07-15

## Implemented source

- `mdstats/analysis/diffusion.py`;
- public exports from `mdstats.analysis`;
- top-level public exports from `mdstats`.

## Public API

```python
estimate_diffusion_plateau(
    running,
    *,
    time_range_ps=None,
    minimum_points=8,
    slope_tolerance=None,
    method="explicit",
)

compare_msd_vacf_diffusion(
    msd,
    vacf_diffusion,
    *,
    msd_fit_range_ps,
    dimensions=3,
)
```

## Scientific contract

- GK2 accepts only an explicit user-selected interval in this release;
- existing lag samples are selected without interpolation;
- the interval arithmetic mean is the reported VACF diffusion estimate;
- centered linear diagnostics expose drift and residual structure;
- an optional slope tolerance records pass/fail but does not auto-select a window;
- no independent-sample standard error is inferred from one serially correlated running curve;
- `stable_window` and tail fitting remain explicitly deferred;
- GK3 fits a time-averaged laboratory-frame MSD with an intercept;
- scalar and Cartesian Einstein factors are handled separately;
- atom, drift, source, component, and dimensional compatibility are enforced;
- signed, absolute, and symmetric relative differences are reported without a preferred estimator;
- negative slopes and failed or unassessed VACF stability remain visible as diagnostics.

## Provenance boundary

The long-time MSD relation is attributed to Einstein (1905), DOI
`10.1002/andp.19053220806`. The VACF estimate remains grounded in Green
(1954), DOI `10.1063/1.1740082`, and Kubo (1957), DOI
`10.1143/JPSJ.12.570`. The explicit interval estimator, centered diagnostic
implementation, uncertainty refusal, compatibility guards, result schemas,
and symmetric comparison measure are mdstats designs.

## Focused validation

```text
tests/test_diffusion.py
```

Coverage includes explicit plateau selection, boundary-only sample selection,
slope diagnostics, stable-window deferral, missing uncertainty claims, exact
scalar and directional comparisons, symmetric disagreement, semantic and
provenance mismatch rejection, negative-slope flags, public imports, and result
identity validation.
