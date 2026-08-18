# Creating an mdstats VASP CONTCAR trajectory

This directory contains an example workflow for preserving VASP's native
per-step Cartesian ionic velocities when an HDF5 trajectory is unavailable.
The resulting `TRAJECTORY` is a custom mdstats input format, not a native VASP
output filename.

## Files

- `watch_contcar.sh`: polls the live `CONTCAR`, verifies that a candidate copy
  is stable while being copied, removes duplicates, and writes zero-padded
  snapshots such as `velocity_frames/CONTCAR.00000001`.
- `vasp_contcar.sh`: removes a stale pre-run `CONTCAR`, launches the watcher in
  the background, runs VASP, and stops the watcher after a final grace period.

Edit the `srun /path/to/vasp_std` line in `vasp_contcar.sh` for the local VASP
executable and scheduler. Then run:

```bash
chmod +x watch_contcar.sh vasp_contcar.sh
./vasp_contcar.sh
```

The snapshot names are padded to eight digits, so shell glob order is also
chronological order. To create the custom stream, enter the snapshot directory
and concatenate the files exactly as follows:

```bash
cd velocity_frames
cat CONTCAR.* > TRAJECTORY
```

Equivalently, from the VASP working directory:

```bash
cat velocity_frames/CONTCAR.* > TRAJECTORY
```

Do not concatenate `CONTCAR.before_md` or other nonnumeric files. The watcher
counter is a captured-snapshot sequence. It equals the VASP ionic-step number
only when every CONTCAR update is observed and archived.

Read the result with an explicit saved-frame spacing:

```python
from mdstats import read_vasp_frames

trajectory = read_vasp_frames(
    "TRAJECTORY",
    format="vasp-contcar-trajectory",
    timestep_fs=1.0,
)
```

`timestep_fs` is the physical spacing between adjacent archived records, not
necessarily the VASP `POTIM`. If one snapshot is saved every fifth ionic step
and `POTIM = 1 fs`, pass `timestep_fs=5.0`.

The reader requires the native Cartesian velocity block in every record. It
never substitutes finite-difference velocities for this format.
