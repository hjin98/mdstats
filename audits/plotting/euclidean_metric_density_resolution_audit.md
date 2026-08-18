# Euclidean metric and density-resolution audit

## Finding

The Plotly scene preserves the Cartesian Euclidean metric. For the Na-LTA
all-species example, the final Cartesian range extents are

- x: 37.5040951524 angstrom,
- y: 21.7404062456 angstrom,
- z: 18.6578042853 angstrom.

The manual Plotly aspect ratio is

- x: 1.0,
- y: 0.5796808630,
- z: 0.4974871200.

The aspect length divided by axis range is the same for all three axes, so one
angstrom has one common display scale. The primitive cell vectors also retain
equal lengths and approximately 60-degree mutual angles.

## Root cause of the apparent uniform ellipticity

The previous all-species example used a 48^3 grid and a 0.22 angstrom Gaussian
bandwidth. In the LTA primitive cell, the real-space grid-edge length is about
0.362 angstrom, giving sigma / h about 0.61. A Gaussian narrower than one grid
interval is under-resolved. Cloud-in-cell deposition plus marching-cubes
interpolation then produces a systematic apparent elongation in the oblique
cell.

A synthetic stationary isotropic Gaussian reproduced the same elongation, so
this part of the effect was numerical rather than physical.

## Corrective changes

- AtomicDensityOptions default grid: 96^3.
- AtomicDensityOptions default Gaussian bandwidth: 0.35 angstrom.
- FrameworkDensityOptions receives the same defaults.
- Framework density smooth mesh rendering is restored as the default.
- Preparation emits a RuntimeWarning when sigma / longest_grid_edge < 1.5.
- Added an isotropic-shell regression in the 60-degree LTA primitive cell;
  the default 50% shell has radial max/min below 1.10.

## Physical anisotropy check

Raw registered atomic trajectories do show site-dependent anisotropic thermal
motion. However, their principal axes vary by site and species; they do not
share one uniform global stretch direction. Thus the corrected plot may still
show physically elliptical individual clouds, but the common axis bias from
under-resolution is removed.
