# VP1 velocity-spectrum plotting implementation audit

Release target: `mdstats 0.19.3a0`  
Date: 2026-07-15

## Implemented source

- `mdstats/plotting/velocity_spectrum.py`;
- public export from `mdstats.plotting`;
- top-level public export from `mdstats`.

## Public API

```python
plot_velocity_spectrum(
    result,
    *,
    x_axis="thz",
    projection="total",
    atom_indices=None,
    normalize_for_display=False,
    ax=None,
)
```

The function accepts `VelocitySpectrumResult` or `VDOSResult` and returns the
owning `(Figure, Axes)` pair.

## Plotting contract

- THz, inverse-centimeter, and meV axes use stored result coordinates;
- ordinate arrays remain densities with respect to the canonical THz grid;
- total, Cartesian, and scalar per-atom projections are supported;
- more than twelve implicit per-atom curves require an explicit subset;
- requested canonical atom indices preserve user order and are never silently
  omitted;
- display normalization uses one common maximum-absolute scale across selected
  curves and operates on copies;
- labels distinguish velocity spectral density from VDOS and never introduce a
  phonon-DOS claim;
- file writing, showing, peak finding, and scientific recomputation are absent.

## Provenance boundary

Rendering uses Matplotlib and cites Hunter (2007), DOI
`10.1109/MCSE.2007.55`. The result-aware labels, bounded atom guard, common
display scale, no-Jacobian horizontal-axis policy, and API schema are mdstats
designs. No new borrowed numerical transform or quadrature method is introduced
in VP1.

## Focused validation

```text
tests/test_plot_velocity_spectrum.py
```

Coverage includes all horizontal axes, velocity-spectrum and VDOS labels,
Cartesian and per-atom selection, implicit-curve bounds, invalid atom requests,
result immutability, common-scale display normalization, axes reuse, public
imports, and invalid option rejection.
