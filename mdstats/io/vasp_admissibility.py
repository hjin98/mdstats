"""VASP convenience entry point for Stage 11E-STAT2 admissibility."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .admissibility import (
    EnsembleAdmissibilityPolicy,
    EnsembleApproximationProvenance,
    PmfAdmissibilityCertificate,
    ReweightingProvenance,
    assess_pmf_admissibility,
)
from .production_regimes import ProductionWindowPolicy, assess_production_regimes
from .trajectory_quality import TrajectoryQualityPolicy, assess_trajectory_quality
from .vasp import read_vasp_frames
from .vasp_controls import read_vasp_run_controls
from .vasp_ensemble import certify_vasp_simulation_controls


def assess_vasp_pmf_admissibility(
    source: str | Path,
    *,
    companion_files: Mapping[str, str | Path] | None = None,
    quality_policy: TrajectoryQualityPolicy | None = None,
    production_window_policy: ProductionWindowPolicy | None = None,
    admissibility_policy: EnsembleAdmissibilityPolicy | None = None,
    reweighting_provenance: ReweightingProvenance | None = None,
    approximation_provenance: EnsembleApproximationProvenance | None = None,
) -> PmfAdmissibilityCertificate:
    """Reconstruct ENS0-STAT1 and return a source-bound STAT2 certificate."""

    bundle = read_vasp_run_controls(source, companion_files=companion_files)
    controls = certify_vasp_simulation_controls(bundle)
    collection = read_vasp_frames(
        source,
        assess_quality=False,
        assess_stationarity=False,
        assess_admissibility=False,
    )
    quality = assess_trajectory_quality(
        collection,
        energy_catalog=bundle.energy_catalog,
        numerical_quality_controls=bundle.numerical_quality_controls,
        simulation_control_certificate=controls,
        source_identity_signature=bundle.source_identity.signature,
        policy=quality_policy,
        emit_warning=False,
        raise_on_unqualified=False,
    )
    regimes = assess_production_regimes(
        collection,
        energy_catalog=bundle.energy_catalog,
        simulation_control_certificate=controls,
        trajectory_quality_verdict=quality,
        source_identity_signature=bundle.source_identity.signature,
        policy=production_window_policy,
    )
    return assess_pmf_admissibility(
        simulation_control_certificate=controls,
        trajectory_quality_verdict=quality,
        production_regime_catalog=regimes,
        source_identity_signature=bundle.source_identity.signature,
        policy=admissibility_policy,
        reweighting_provenance=reweighting_provenance,
        approximation_provenance=approximation_provenance,
    )


__all__ = ["assess_vasp_pmf_admissibility"]
