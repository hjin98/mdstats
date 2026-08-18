# Examples

Rendered examples and their generation scripts are grouped by feature rather than placed at the package root.

- `graph_visualization/2d/`: static Matplotlib graph views.
- `graph_visualization/3d/`: downloadable interactive HTML graph views.
- `graph_visualization/framework_topology/`: projected-framework and atomic-path examples.
- `graph_visualization/tuned/`: retained rendering-tuning examples.

Three-dimensional examples are files for external viewing and are not embedded in package documentation.

- `topology_statistics/na_lta_300K/`: TS5 statistical figures and table exports for the 2,000-frame Na-LTA trajectory.

- `primitive_ring/na_lta_300K/`: deterministic S4 ring catalog, search diagnostics, and tables for the uniform Na-LTA framework topology.
- `vacf_dynamics/`: native-velocity VDOS and running Green-Kubo diffusion example for watcher-generated VASP `TRAJECTORY` files.
## Running top-level examples from the source checkout

The mixed-alkali LTA density example can be launched directly from this
directory; no editable installation is required:

```bash
cd examples
python plot_lta_mixed_alkali_density.py /path/to/TRAJECTORY
```

The same example accepts every time-ordered trajectory source currently exposed
by mdstats: VASP `vasprun.xml`, VASP `XDATCAR`, watcher-generated concatenated
CONTCAR `TRAJECTORY` files, and native LAMMPS custom dumps. Common filenames are
auto-detected. Examples:

```bash
# VASP XML; POTIM is read from vasprun.xml.
python plot_lta_mixed_alkali_density.py /path/to/vasprun.xml

# XDATCAR needs the saved-frame spacing because XDATCAR does not contain POTIM.
python plot_lta_mixed_alkali_density.py /path/to/XDATCAR --timestep-fs 1.0

# LAMMPS dump containing an `element` column and embedded TIME/UNITS records.
python plot_lta_mixed_alkali_density.py /path/to/run.lammpstrj

# Numeric LAMMPS types, with units/timestep and thermo metadata supplied by the log.
python plot_lta_mixed_alkali_density.py /path/to/dump.production \
  --lammps-log /path/to/log.lammps \
  --lammps-type-map '1=Si,2=Al,3=O,4=Li,5=Na,6=K'

# Ambiguous filename: override format explicitly.
python plot_lta_mixed_alkali_density.py /path/to/frames.dat \
  --format lammps-dump --lammps-units metal --lammps-timestep 0.001 \
  --lammps-type-map '1=Si,2=Al,3=O,4=Na'
```

`--stride` is applied by the selected mdstats trajectory reader, so the plotting
pipeline receives only the requested frames. For a LAMMPS dump, `--lammps-log`
is optional but recommended when the dump itself does not contain `ITEM: TIME`
and `ITEM: UNITS`, or when thermo quantities should be attached to the frames.

When the script is located inside the source checkout, it automatically places
the adjacent repository root at the front of `sys.path` and imports that exact
`mdstats` source tree. This avoids accidentally using an older separately
installed package. If the script is copied elsewhere, it does not modify
`sys.path` and instead imports the installed package normally. Runtime
dependencies such as ASE, SciPy, Plotly, scikit-image, and threadpoolctl must
still be installed in the active Python environment.


### Stage 11E8a-S3 structural mapping and temporal preparation

```bash
python site_discovery/na_lta_300K_stage11e8a_structural_temporal.py /path/to/vasprun.xml
```

This example maps the central exploratory Na attractors to actual serrated
primitive-ring oxygen polygons and applies the exact coordinate-identical
partition to the full trajectory for provisional Stage 11E4 temporal support.
It does not publish final events, paths, or rates.

### Stage 11E8a-S4 force-density and path readiness

```bash
python site_discovery/na_lta_300K_stage11e8a_force_paths.py /path/to/vasprun.xml
```

This example executes the provenance-strict E3 force boundary and reports
whether final Stage 11E6/E6b path reconstruction is admissible. Complete forces
are not treated as equilibrium PMF evidence, and unresolved S2/E5 prerequisites
remain explicit blockers.

- `mlff_precision_policy.py`: choose protocol-bound float32 or float64 MACE fine-tuning precision while retaining an unmodified float64 MPA-0 checkpoint.
