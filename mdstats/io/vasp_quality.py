"""VASP convenience adapter for Stage 11E-STAT0 quality assessment."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .trajectory_quality import (
    TrajectoryQualityPolicy,
    TrajectoryQualityVerdict,
    assess_trajectory_quality,
)
from .vasp import read_vasp_frames
from .vasp_controls import read_vasp_run_controls
from .vasp_ensemble import certify_vasp_simulation_controls


def assess_vasp_trajectory_quality(
    filename: str | Path,
    *,
    companion_files: Mapping[str, str | Path] | None = None,
    policy: TrajectoryQualityPolicy | None = None,
    emit_warning: bool = True,
    raise_on_unqualified: bool = True,
) -> TrajectoryQualityVerdict:
    """Assess one complete unstrided ``vasprun.xml`` trajectory."""

    bundle = read_vasp_run_controls(filename, companion_files=companion_files)
    certificate = certify_vasp_simulation_controls(
        bundle, companion_files=companion_files
    )
    collection = read_vasp_frames(
        str(filename),
        format="vasp-xml",
        assess_quality=False,
        assess_stationarity=False,
    )
    return assess_trajectory_quality(
        collection,
        energy_catalog=bundle.energy_catalog,
        numerical_quality_controls=bundle.numerical_quality_controls,
        simulation_control_certificate=certificate,
        source_identity_signature=bundle.source_identity.signature,
        policy=policy,
        emit_warning=emit_warning,
        raise_on_unqualified=raise_on_unqualified,
    )


__all__ = ["assess_vasp_trajectory_quality"]
