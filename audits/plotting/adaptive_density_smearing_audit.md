# Adaptive density smearing audit

## Scope

This audit covers the 0.19.39a0 density-resolution policy for atomic occupancy,
framework vertex occupancy, and framework edge-length density fields.

## Implemented policy

- The default Gaussian bandwidth is no longer an independent fixed number.
- With `gaussian_bandwidth=None`, the resolved bandwidth is
  `gaussian_to_grid_ratio * max(realized_grid_intervals)`.
- The default ratio is 2.0.
- Per selected atom, or per framework vertex, the code computes a periodic
  Cartesian positional standard deviation
  `sqrt(trace(periodic_covariance) / 3)`.
- The field-level reference is the configurable quantile of the per-item SDs;
  the default is the 10th percentile.
- Automatic refinement is triggered when the nominal Gaussian bandwidth
  exceeds `max_smearing_to_sample_sd_ratio * reference_sd`; the default ratio
  is 0.5.
- The grid interval and Gaussian are reduced together so their fixed ratio is
  preserved.

## Periodic metric

The periodic mean and covariance use minimum-image Cartesian displacements in
the full display-cell metric. The construction is invariant under integer
lattice-image changes and supports triclinic cells.

The mean is the flat-torus specialization of the Frechet/Karcher center of
mass. Code comments and specifications cite Frechet (1948) and Karcher (1977).

## Resource boundary

A narrow physical distribution can imply a prohibitively large global 3-D
grid. The implementation therefore assigns each requested field an equal share
of `max_density_voxels` and refines only within that share.

If the requested SD criterion cannot be reached:

1. the finest grid within the budget is used;
2. the Gaussian remains coupled to the realized interval;
3. a `RuntimeWarning` reports the residual `sigma / reference_sd` ratio; and
4. field metadata records `adaptive_smearing_budget_limited=True`.

This limitation is not hidden. A budget-limited result is improved relative to
the nominal grid but is not claimed to separate physical and artificial
broadening completely.

## Explicit overrides

An explicit `grid_shape` or explicit `gaussian_bandwidth` remains authoritative.
The code computes the SD diagnostic and warns when the explicit setting is
large relative to the measured spread, but it does not silently modify the
explicit value.

## Na-LTA example

For the four all-species fields with a total voxel budget of 5,000,000, each
field receives 1,250,000 voxels. The nominal 87^3 grid and approximately
0.39915 A Gaussian refine to approximately 107 x 108 x 108 and 0.32454 A.
The requested 0.5 SD criterion remains budget-limited for all four species, and
the generated warnings report that fact.
