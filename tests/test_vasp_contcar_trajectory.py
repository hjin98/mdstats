from __future__ import annotations

import gzip
from pathlib import Path

import numpy as np
import pytest

from mdstats import compute_vacf, compute_velocity_spectrum, read_vasp_frames
from mdstats.exceptions import (
    InconsistentVaspRecordError,
    MissingNativeVelocityError,
    MissingTimeError,
    TruncatedVaspRecordError,
)
from mdstats.io.vasp_contcar_trajectory import VaspContcarTrajectoryWarning


def _record(
    *,
    x: float,
    velocity: float,
    potim: float = 1.0,
    symbols: tuple[str, ...] = ("Na",),
    counts: tuple[int, ...] = (1,),
    scale_line: str = "1.0",
    cell_lines: tuple[str, str, str] = (
        "10 0 0",
        "0 10 0",
        "0 0 10",
    ),
    cartesian_positions: bool = False,
    selective: bool = False,
    lattice_velocities: bool = False,
    velocity_mode: str = "",
    include_predictor: bool = True,
) -> str:
    n_atoms = sum(counts)
    lines = [
        "synthetic MD CONTCAR",
        scale_line,
        *cell_lines,
        " ".join(symbols),
        " ".join(str(value) for value in counts),
    ]
    if selective:
        lines.append("Selective dynamics")
    lines.append("Cartesian" if cartesian_positions else "Direct")
    for atom in range(n_atoms):
        position = f"{x + atom * 0.1:.8f} 0.0 0.0"
        if selective:
            position += " T F T"
        lines.append(position)

    if lattice_velocities:
        lines.extend(
            [
                "Lattice velocities and vectors",
                "1",
                "0 0 0",
                "0 0 0",
                "0 0 0",
                "10 0 0",
                "0 10 0",
                "0 0 10",
            ]
        )
    lines.append(velocity_mode)
    for atom in range(n_atoms):
        lines.append(f"{velocity + atom * 0.001:.8e} 0.0 0.0")

    if include_predictor:
        lines.extend(["", "1", f"{potim:.16f}", "1 0 0 0"])
        for block in range(3):
            for atom in range(n_atoms):
                lines.append(f"{x + block + atom * 0.1:.8e} 0.0 0.0")
    return "\n".join(lines) + "\n"


def _read(path: Path, **kwargs):
    return read_vasp_frames(
        str(path),
        format="vasp-contcar-trajectory",
        timestep_fs=kwargs.pop("timestep_fs", 1.0),
        **kwargs,
    )


def test_reads_native_velocities_without_finite_difference_fallback(tmp_path: Path) -> None:
    path = tmp_path / "TRAJECTORY"
    path.write_text(
        _record(x=0.90, velocity=0.001) + _record(x=0.00, velocity=0.002),
        encoding="utf-8",
    )

    trajectory = _read(path)

    assert trajectory.n_frames == 2
    assert trajectory.n_atoms == 1
    np.testing.assert_allclose(trajectory.times, [0.0, 0.001])
    np.testing.assert_allclose(trajectory.fractional_positions[:, 0, 0], [0.9, 1.0])
    np.testing.assert_allclose(trajectory.velocities[:, 0, 0], [1.0, 2.0])
    assert trajectory.steps is None
    assert trajectory.provenance.velocity_source == "native"
    assert trajectory.provenance.source_format == "vasp-contcar-trajectory"
    assert trajectory.metadata["velocity_block_required"] is True
    assert trajectory.metadata["velocity_conversion_to_internal"] == 1000.0


def test_requires_explicit_saved_frame_timestep(tmp_path: Path) -> None:
    path = tmp_path / "TRAJECTORY"
    path.write_text(_record(x=0.0, velocity=0.001), encoding="utf-8")
    with pytest.raises(MissingTimeError, match="Supply timestep_fs explicitly"):
        read_vasp_frames(
            str(path),
            format="vasp-contcar-trajectory",
            timestep_fs=None,
        )


def test_missing_or_direct_velocity_block_is_a_hard_error(tmp_path: Path) -> None:
    direct = tmp_path / "direct.TRAJECTORY"
    direct.write_text(
        _record(x=0.0, velocity=0.001, velocity_mode="Direct"),
        encoding="utf-8",
    )
    with pytest.raises(MissingNativeVelocityError, match="native Cartesian"):
        _read(direct, reconstruct_velocities=True)

    missing = tmp_path / "missing.TRAJECTORY"
    lines = _record(x=0.0, velocity=0.001).splitlines()
    # Remove the blank velocity mode so the first numeric velocity is consumed as mode.
    del lines[9]
    missing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(MissingNativeVelocityError):
        _read(missing, reconstruct_velocities=True)


def test_selection_preserves_source_record_time(tmp_path: Path) -> None:
    path = tmp_path / "TRAJECTORY"
    path.write_text(
        "".join(_record(x=0.1 * i, velocity=0.001 * (i + 1)) for i in range(6)),
        encoding="utf-8",
    )
    trajectory = _read(path, start=1, stop=6, stride=2, timestep_fs=2.0)
    np.testing.assert_allclose(trajectory.times, [0.002, 0.006, 0.010])
    np.testing.assert_allclose(trajectory.velocities[:, 0, 0], [2.0, 4.0, 6.0])
    assert trajectory.metadata["selected_source_record_indices"] == (1, 3, 5)
    assert trajectory.metadata["source_frame_count"] == 6
    assert trajectory.metadata["implied_save_stride"] == 2


def test_selective_cartesian_component_scaling_and_lattice_velocity_block(
    tmp_path: Path,
) -> None:
    path = tmp_path / "TRAJECTORY"
    path.write_text(
        _record(
            x=0.5,
            velocity=0.003,
            scale_line="2 3 4",
            cell_lines=("1 0 0", "0 1 0", "0 0 1"),
            cartesian_positions=True,
            selective=True,
            lattice_velocities=True,
        ),
        encoding="utf-8",
    )
    trajectory = _read(path)
    np.testing.assert_allclose(trajectory.cells[0], np.diag([2.0, 3.0, 4.0]))
    np.testing.assert_allclose(trajectory.fractional_positions[0, 0], [0.5, 0.0, 0.0])
    np.testing.assert_allclose(trajectory.velocities[0, 0], [3.0, 0.0, 0.0])
    assert trajectory.metadata["selective_dynamics_present"] is True
    assert trajectory.metadata["lattice_velocity_block_present"] is True
    assert trajectory.metadata["position_coordinate_modes"] == ("cartesian",)


def test_species_change_and_truncated_predictor_are_rejected(tmp_path: Path) -> None:
    inconsistent = tmp_path / "inconsistent.TRAJECTORY"
    inconsistent.write_text(
        _record(x=0.0, velocity=0.001)
        + _record(x=0.1, velocity=0.001, symbols=("K",)),
        encoding="utf-8",
    )
    with pytest.raises(InconsistentVaspRecordError, match="species names"):
        _read(inconsistent)

    truncated = tmp_path / "truncated.TRAJECTORY"
    text = _record(x=0.0, velocity=0.001)
    truncated.write_text("\n".join(text.splitlines()[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(TruncatedVaspRecordError, match="predictor array"):
        _read(truncated)


def test_potim_diagnostics_and_mass_override(tmp_path: Path) -> None:
    path = tmp_path / "TRAJECTORY"
    path.write_text(
        _record(x=0.0, velocity=0.001, potim=1.0)
        + _record(x=0.1, velocity=0.002, potim=2.0),
        encoding="utf-8",
    )
    with pytest.raises(InconsistentVaspRecordError, match="POTIM changes"):
        _read(path, strict=True)

    with pytest.warns(VaspContcarTrajectoryWarning, match="POTIM changes"):
        trajectory = _read(path, strict=False, mass_map={"Na": 23.5})
    np.testing.assert_allclose(trajectory.masses, [23.5])
    assert trajectory.metadata["mass_source"] == "explicit mass_map"


def test_compressed_input_and_downstream_velocity_analysis(tmp_path: Path) -> None:
    path = tmp_path / "TRAJECTORY.gz"
    text = "".join(
        _record(x=(0.01 * i) % 1.0, velocity=0.001 * np.cos(i / 3.0))
        for i in range(16)
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)

    trajectory = _read(path)
    vacf = compute_vacf(trajectory, max_lag=5)
    spectrum = compute_velocity_spectrum(
        trajectory,
        segment_length=8,
        overlap=0.5,
        window="hann",
    )
    assert vacf.metadata["velocity_source"] == "native"
    assert spectrum.metadata["velocity_source"] == "native"
    assert spectrum.frequencies_thz.size == 5
