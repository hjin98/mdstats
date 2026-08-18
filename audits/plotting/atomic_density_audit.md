# Plot-D3 Atomic-Density Implementation Audit

Release: `mdstats 0.19.31a0`

## Implemented boundary

Plot-D3 adds one renderer-independent atomic occupancy field to the existing
registered framework-dynamics scene. The implementation:

- reuses the exact Plot-D1 display cell and registration drift;
- accepts trajectories and independent ensembles;
- resolves explicit atoms and species into immutable source sets;
- deposits normalized occupancy by periodic trilinear cloud-in-cell assignment;
- performs Cartesian-isotropic Gaussian smoothing in reciprocal space;
- renormalizes every field to the exact selected-atom count;
- stores density in `angstrom^-3` on an immutable fractional grid;
- derives highest-density superlevel thresholds from enclosed probability mass;
- closes the periodic seam before Plotly isosurface rendering;
- optionally retains and renders raw folded samples;
- keeps every density layer independently togglable over the mean framework;
- rejects mixed periodicity and every exceeded resource limit explicitly.

## External methods

The cloud-in-cell assignment is adapted from Hockney and Eastwood, *Computer
Simulation Using Particles* (1988). Highest-density probability-mass regions are
adapted from R. J. Hyndman, *The American Statistician* 50, 120-126 (1996), DOI
`10.1080/00031305.1996.10474359`. Plotly supplies only the optional interactive
isosurface trace.

The periodic registration, framework-drift reuse, triclinic reciprocal metric,
normalization policy, transformed shell field, seam closure, resource accounting,
and composite viewer integration are project-specific implementations.

## Deliberate limitations

- uniform frame weights;
- fully periodic cells;
- uniform fractional grids;
- one Gaussian bandwidth per scene preparation call;
- no covariance glyphs, rolling windows, or difference fields;
- no framework edge-length density, which remains Plot-D4.

No limitation is converted into an implicit approximation.
