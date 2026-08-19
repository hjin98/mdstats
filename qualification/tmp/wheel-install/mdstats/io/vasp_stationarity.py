"""VASP convenience adapter for Stage 11E-STAT1 production regimes."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .production_regimes import (
    ProductionRegimeCatalog,
    ProductionWindowPolicy,
    assess_production_regimes,
)
from .trajectory_quality import TrajectoryQualityPolicy, assess_trajectory_quality
from .vasp import read_vasp_frames
from .vasp_controls import read_vasp_run_controls
from .vasp_ensemble import certify_vasp_simulation_controls


def assess_vasp_production_regimes(
    filename: str | Path,
    *,
    companion_files: Mapping[str, str | Path] | None = None,
    quality_policy: TrajectoryQualityPolicy | None = None,
    production_window_policy: ProductionWindowPolicy | None = None,
    emit_quality_warning: bool = True,
    raise_on_unqualified: bool = True,
) -> ProductionRegimeCatalog:
    """Assess one complete unstrided ``vasprun.xml`` production-regime catalog."""

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
    quality = assess_trajectory_quality(
        collection,
        energy_catalog=bundle.energy_catalog,
        numerical_quality_controls=bundle.numerical_quality_controls,
        simulation_control_certificate=certificate,
        source_identity_signature=bundle.source_identity.signature,
        policy=quality_policy,
        emit_warning=emit_quality_warning,
        raise_on_unqualified=raise_on_unqualified,
    )
    return assess_production_regimes(
        collection,
        energy_catalog=bundle.energy_catalog,
        simulation_control_certificate=certificate,
        trajectory_quality_verdict=quality,
        source_identity_signature=bundle.source_identity.signature,
        policy=production_window_policy,
    )


__all__ = ["assess_vasp_production_regimes"]
