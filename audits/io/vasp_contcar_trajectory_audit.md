# VASP CONTCAR trajectory reader implementation audit

Release target: `mdstats 0.19.8a0`.

## Scope

This audit covers the custom `vasp-contcar-trajectory` source reader, the
watcher/caller examples, native-velocity invariants, focused synthetic tests,
and acceptance against the supplied real files.

## Implemented source contract

- explicit format selection through `read_vasp_frames()`;
- mandatory explicit saved-frame `timestep_fs`;
- complete POSCAR/CONTCAR record parsing;
- mandatory Cartesian native velocity block;
- exact `1000` conversion from Angstrom/fs to Angstrom/ps;
- no finite-difference fallback;
- three `N x 3` predictor arrays consumed for exact record framing;
- fixed species/count ordering, variable cells, periodic unwrapping;
- compressed text and optional mass overrides;
- line- and record-aware errors.

## Focused synthetic validation

`tests/test_vasp.py` and `tests/test_vasp_contcar_trajectory.py` verify legacy
VASP XML/XDATCAR behavior and the new custom path. Covered cases include native
velocity preservation, missing velocity hard failures, selection timing,
selective dynamics, Cartesian scaling, lattice velocities, species changes,
truncation, POTIM diagnostics, mass overrides, compressed input, VACF, and the
direct Welch estimator.

## Real-file acceptance

Files supplied outside the source distribution:

```text
CONTCAR.00000001
TRAJECTORY
```

Observed and verified:

```text
standalone records:             1
concatenated records:           1500
atoms per record:               168
species counts:                 Si 24, Al 24, O 96, Na 24
trajectory time range:          0.000 to 1.499 ps at dt = 1 fs
velocity array shape:           (1500, 168, 3)
velocity provenance:            native
all velocity entries finite:    yes
first record exact agreement:   cell, positions, velocities
VACF native-velocity input:      passed
Welch native-velocity input:     passed
```

The first atom velocity was parsed as

```text
[1.3084504, 2.1781006, -0.36173608] Angstrom/ps
```

from the CONTCAR text value in Angstrom/fs.

## Documentation boundary

Official VASP POSCAR/CONTCAR rules are attributed to the VASP Wiki. The
multi-record concatenation, watcher recipe, strict native-velocity policy,
three-array framing assumption, metadata, and errors are explicitly described
as mdstats designs.
