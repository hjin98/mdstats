#!/usr/bin/env python3
"""Compatibility launcher for the historical mixed-alkali LTA 3-D example.

New work should use ``tools/mdstats-3d.py`` or the installed ``mdstats-3d``
command. This shim preserves the old example entry point and its trajectory
input helper functions while delegating plotting to the universal GFX3D CLI.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mdstats import read_lammps_frames, read_vasp_frames
from mdstats.graphics3d.cli import main
from mdstats.graphics3d.lta_preset import infer_trajectory_format, parse_lammps_type_map


def read_input_trajectory(args):
    """Historical argparse-namespace wrapper retained for compatibility."""
    source_format = infer_trajectory_format(args.trajectory, args.format)
    if source_format == "lammps-dump":
        trajectory = read_lammps_frames(
            str(args.trajectory),
            log_file=None if args.lammps_log is None else str(args.lammps_log),
            units=args.lammps_units,
            timestep=args.lammps_timestep,
            type_map=parse_lammps_type_map(args.lammps_type_map),
            stride=args.stride,
        )
        return trajectory, source_format
    timestep_fs = args.timestep_fs
    if source_format == "vasp-contcar-trajectory" and timestep_fs is None:
        timestep_fs = 1.0
    trajectory = read_vasp_frames(
        str(args.trajectory),
        format=source_format,
        stride=args.stride,
        timestep_fs=timestep_fs,
    )
    return trajectory, source_format


def _compat_argv(argv: list[str]) -> list[str]:
    configured = "--config" in argv or any(value.startswith("--config=") for value in argv)
    explicit_layers = "--layer" in argv or any(value.startswith("--layer=") for value in argv)
    explicit_preset = any(value == "--preset" or value.startswith("--preset=") for value in argv)
    result = list(argv)
    if not (configured or explicit_layers or explicit_preset):
        result.extend(["--preset", "lta-mixed-alkali-density"])
    explicit_output = "--output" in result or any(value.startswith("--output=") for value in result)
    if not configured and not explicit_output:
        result.extend(["--output", "lta_density_framework_trajectories.html"])
    return result


if __name__ == "__main__":
    raise SystemExit(main(_compat_argv(sys.argv[1:])))
