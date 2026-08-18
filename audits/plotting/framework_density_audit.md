# Plot-D4 Framework Density Implementation Audit

Release: `mdstats 0.19.32a0`

## Implemented source boundary

- `mdstats/plotting/framework_density.py`
- `mdstats/plotting/framework_dynamics.py`
- `mdstats/plotting/__init__.py`
- `mdstats/__init__.py`
- `tests/test_framework_density.py`

## Scientific channels

The implementation stores two independent `PeriodicScalarField3D` records:

1. `framework-vertex-density`, normalized to the number of projected framework
   vertices and reported in `angstrom^-3`;
2. `framework-edge-length-density`, normalized to the frame-weighted total
   retained arc length and reported in `angstrom^-2`.

The channels are not combined numerically. Their different physical dimensions
are recorded in field metadata and in the normative specification.

## Geometry and periodicity

- Projected framework vertices always define the vertex channel.
- Projected edge mode uses the canonical lifted projected edge and preserves
  decorated parallel-edge multiplicity.
- Atomic-path mode uses the authoritative retained path segments in
  `FrameworkTopology`; it does not infer bonds from geometry.
- Periodic gauges and residual edge shifts are replayed for every selected frame.
- Laboratory-mode image shifts are transformed through the instantaneous cell
  before being expressed in display-cell fractional coordinates.
- Framework-registered mode applies the same translational drift correction to
  the mean graph, atomic fields, vertex field, and edge field.

## Numerical backend

- Vertex samples use normalized frame weights.
- Edge segments use uniform midpoint arc-length quadrature.
- Quadrature weights sum exactly to each frame-weighted segment length.
- Both channels reuse periodic trilinear cloud-in-cell deposition.
- Both channels reuse normalized Cartesian-isotropic reciprocal-space Gaussian
  smoothing for triclinic display cells.
- Final normalization is explicitly restored after floating-point FFT operations.

## Rendering

- Framework fields reuse the seam-closed highest-density isosurface backend.
- Vertex and edge fields have independent stable field keys and legend groups.
- Framework defaults use lower opacity than atomic occupancy fields.
- Rendering remains optional; Plotly is not imported during field preparation.
- `FrameworkDynamicsRenderResult` reports framework trace indices separately
  from atomic-density trace indices.

## Resource and failure semantics

The implementation preflights:

- combined atomic and framework field count;
- combined voxel allocation;
- vertex sample count;
- edge quadrature sample count;
- rendered seam-closed grid points;
- density trace count;
- total Plotly trace count.

The first backend explicitly rejects mixed periodicity and topology-incompatible
frame selections. It does not silently coarsen the grid, increase edge spacing,
omit edges, or merge the two scientific channels.

## External methods

- Cloud-in-cell assignment is adapted from Hockney and Eastwood, *Computer
  Simulation Using Particles*.
- Highest-density probability-mass shells reuse the Plot-D3 construction adapted
  from R. J. Hyndman, "Computing and Graphing Highest Density Regions," *The
  American Statistician* 50 (1996), 120-126.
- Plotly `Isosurface` is only an optional rendering backend.

The framework point/line measures, their normalization contract, the
projected-versus-atomic-path policy, and the shared registration integration are
project-specific constructions.
