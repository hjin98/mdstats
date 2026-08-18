# Density grid interval audit

## Objective

Replace the fixed atomic- and framework-density default grid shape with a
cell-size-aware target interval while retaining an explicit shape override.

## Implemented policy

For display-cell row vectors `a_i` and requested interval `h`, automatic sizing
uses

\[
N_i = \max\left(4, \left\lceil \frac{\lVert a_i\rVert}{h}\right\rceil\right).
\]

The realized lattice-grid edge length is therefore

\[
h_i = \frac{\lVert a_i\rVert}{N_i} \le h.
\]

The default is `grid_interval=0.20` angstrom with `grid_shape=None`.
An explicit `grid_shape` overrides automatic sizing.

## Na-LTA result

The three primitive vectors have lengths approximately 17.363007 angstrom.
The default resolves to `(87, 87, 87)`, with realized intervals approximately
`(0.19957479, 0.19957479, 0.19957479)` angstrom.

## API changes

- `AtomicDensityOptions.grid_shape` is now optional.
- `AtomicDensityOptions.grid_interval` defaults to 0.20 angstrom.
- `FrameworkDensityOptions.grid_shape` is now optional.
- `FrameworkDensityOptions.grid_interval` defaults to 0.20 angstrom.
- Added public `resolve_density_grid_shape(...)`.
- Added public `density_grid_intervals(...)`.

## Metadata

Each prepared density field records:

- `grid_definition`;
- `grid_shape`;
- `grid_interval_target`; and
- `grid_intervals_realized`.

## Validation

Focused tests cover cubic and triclinic automatic sizing, explicit shape
overrides, metadata, metric-preserving shell extraction, framework-density
integration, resource limits, and existing 3-D plotting behavior.
