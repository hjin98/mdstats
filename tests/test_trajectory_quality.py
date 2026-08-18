from __future__ import annotations

import numpy as np
import pytest

from mdstats.collection import AtomisticFrameCollection
from mdstats.io import (
    DiagnosticRequirement,
    EnsembleKind,
    FrameEnergyCatalog,
    FrameEnergyChannel,
    InferenceStatus,
    NumericalMDQualityControls,
    QualityCheckStatus,
    RealizedEnsembleConsistencyStatus,
    SimulationControlCertificate,
    SimulationControlComponent,
    TrajectoryDegradedQualityWarning,
    TrajectoryIntegrityError,
    TrajectoryQualityOutcome,
    TrajectoryQualityVerdict,
    assess_trajectory_quality,
)
from mdstats.provenance import FrameCollectionProvenance


def _component(kind: str, active: bool | None) -> SimulationControlComponent:
    return SimulationControlComponent(
        status=InferenceStatus.RESOLVED,
        kind=kind,
        active=active,
    )


def _certificate(source_signature: str, ensemble: EnsembleKind = EnsembleKind.NVE) -> SimulationControlCertificate:
    return SimulationControlCertificate(
        source_identity_signature=source_signature,
        source_control_bundle_signature="b" * 64,
        run_controls_signature="c" * 64,
        policy_version="synthetic",
        dynamics_status=InferenceStatus.RESOLVED,
        dynamics_mode="molecular_dynamics",
        ensemble_status=InferenceStatus.RESOLVED,
        ensemble=ensemble,
        propagator=_component("velocity_verlet", True),
        thermostat=_component("none", False),
        barostat=_component("none", False),
        cell_control=_component("fixed_cell", False),
        bias=_component("none", False),
        constraints=_component("none", False),
        force_provenance=_component("synthetic", True),
        initial_velocity_provenance=_component("synthetic", True),
        continuation_provenance=_component("none", False),
        decisions=(),
    )


def _case(*, drift_ev_per_atom_ps: float = 0.0, overlap: bool = False, degraded_controls: bool = False):
    n_frames = 96
    n_atoms = 2
    times = np.arange(n_frames, dtype=float) * 0.001
    rng = np.random.default_rng(123)
    temperature = 300.0 + rng.normal(0.0, 4.0, n_frames)
    dof = 3 * n_atoms - 3
    kinetic = 0.5 * dof * 8.617333262145e-5 * temperature
    total = -10.0 + drift_ev_per_atom_ps * n_atoms * times + rng.normal(0.0, 1.0e-6, n_frames)
    electronic = total - kinetic

    positions = np.zeros((n_frames, n_atoms, 3), dtype=float)
    positions[:, 1, 0] = 0.00001 if overlap else 0.5
    collection = AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(n_frames),
        atomic_numbers=np.array([11, 11], dtype=np.int32),
        masses=np.array([22.99, 22.99]),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames),
        times=times,
        cells=np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=positions,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        forces=np.zeros((n_frames, n_atoms, 3)),
        kinetic_energies=kinetic,
        potential_energies=electronic,
        total_energies=total,
        provenance=FrameCollectionProvenance(
            source_format="vasp-vasprun-xml",
            source_files=("synthetic.xml",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )
    catalog = FrameEnergyCatalog(
        frame_count=n_frames,
        channels=(
            FrameEnergyChannel("kinetic", "ionic_kinetic_energy", "eV", tuple(kinetic)),
            FrameEnergyChannel("e_fr_energy", "electronic_free_energy", "eV", tuple(electronic)),
            FrameEnergyChannel("total", "source_reported_total_energy", "eV", tuple(total)),
        ),
    )
    controls = NumericalMDQualityControls(
        potim_fs=1.0,
        requested_ionic_steps=n_frames,
        present_ionic_steps=n_frames,
        ionic_output_stride=1,
        ediff_ev=1.0e-5 if degraded_controls else 1.0e-7,
        nelm=100,
        nelmin=2,
        algo="Normal",
        ialgo=38,
        prec_explicit="Accurate",
        prec_effective="accura",
        lreal_explicit="Auto" if degraded_controls else False,
        lreal_effective=True if degraded_controls else False,
        ropt=(-2.5e-4,),
        encut_ev=520.0,
        isym=0,
        scf_iteration_counts=(4,) * n_frames,
        scf_iteration_limit_reached=(False,) * n_frames,
        positions_complete=True,
        cells_complete=True,
        forces_complete=True,
        stresses_complete=True,
        native_velocity_frame_count=n_frames,
        energy_channel_completeness=(("kinetic", 1.0), ("e_fr_energy", 1.0), ("total", 1.0)),
    )
    source_signature = "a" * 64
    return collection, catalog, controls, _certificate(source_signature), source_signature


def test_stat0_strict_qualified_temperature_and_energy() -> None:
    collection, catalog, controls, certificate, source_signature = _case()
    verdict = assess_trajectory_quality(
        collection,
        energy_catalog=catalog,
        numerical_quality_controls=controls,
        simulation_control_certificate=certificate,
        source_identity_signature=source_signature,
        emit_warning=False,
    )
    assert verdict.outcome is TrajectoryQualityOutcome.STRICTLY_QUALIFIED
    assert verdict.temperature_definition is not None
    assert verdict.temperature_definition.degrees_of_freedom == 3
    assert verdict.temperature_statistics is not None
    assert verdict.temperature_statistics.represented_time_mean_kelvin == pytest.approx(300.0, abs=2.0)
    assert verdict.energy_conservation.status is QualityCheckStatus.PASS
    assert verdict.realized_ensemble_consistency.status is RealizedEnsembleConsistencyStatus.CONSISTENT
    requirements = {check.check_id: check.requirement for check in verdict.checks}
    assert requirements["integrity.positions_complete"] is DiagnosticRequirement.HARD_INTEGRITY_REQUIRED
    assert requirements["quality.nve_energy_drift"] is DiagnosticRequirement.VERDICT_CRITICAL
    assert requirements["diagnostic.realized_ensemble_consistency"] is DiagnosticRequirement.METHOD_SPECIFIC
    assert verdict.analysis_may_continue


def test_stat0_degraded_quality_warns_and_continues() -> None:
    collection, catalog, controls, certificate, source_signature = _case(
        drift_ev_per_atom_ps=1.2e-3,
        degraded_controls=True,
    )
    with pytest.warns(TrajectoryDegradedQualityWarning) as captured:
        verdict = assess_trajectory_quality(
            collection,
            energy_catalog=catalog,
            numerical_quality_controls=controls,
            simulation_control_certificate=certificate,
            source_identity_signature=source_signature,
        )
    assert len(captured) == 1
    assert verdict.outcome is TrajectoryQualityOutcome.DEGRADED_QUALITY
    assert verdict.analysis_may_continue
    assert "quality.nve_energy_drift" in verdict.degraded_reasons
    assert "quality.ediff" in verdict.degraded_reasons
    assert "quality.lreal" in verdict.degraded_reasons
    assert verdict.realized_ensemble_consistency.status is RealizedEnsembleConsistencyStatus.DEGRADED


def test_stat0_unqualified_overlap_fails_closed() -> None:
    collection, catalog, controls, certificate, source_signature = _case(overlap=True)
    verdict = assess_trajectory_quality(
        collection,
        energy_catalog=catalog,
        numerical_quality_controls=controls,
        simulation_control_certificate=certificate,
        source_identity_signature=source_signature,
        emit_warning=False,
        raise_on_unqualified=False,
    )
    assert verdict.outcome is TrajectoryQualityOutcome.UNQUALIFIED
    assert "integrity.minimum_atomic_distance" in verdict.unqualified_reasons
    with pytest.raises(TrajectoryIntegrityError, match="minimum_atomic_distance"):
        assess_trajectory_quality(
            collection,
            energy_catalog=catalog,
            numerical_quality_controls=controls,
            simulation_control_certificate=certificate,
            source_identity_signature=source_signature,
            emit_warning=False,
        )



def test_stat0_detects_fixed_cell_shape_conflict_without_rejecting() -> None:
    collection, catalog, controls, certificate, source_signature = _case()
    collection.cells[1:, 0, 0] *= 1.01
    collection.cells[1:, 1, 1] /= 1.01
    verdict = assess_trajectory_quality(
        collection,
        energy_catalog=catalog,
        numerical_quality_controls=controls,
        simulation_control_certificate=certificate,
        source_identity_signature=source_signature,
        emit_warning=False,
    )
    assert verdict.outcome is TrajectoryQualityOutcome.DEGRADED_QUALITY
    assert verdict.analysis_may_continue
    assert verdict.realized_ensemble_consistency.status is RealizedEnsembleConsistencyStatus.INCONSISTENT
    assert verdict.realized_ensemble_consistency.cell_volume_relative_range == pytest.approx(0.0, abs=1.0e-12)
    assert verdict.realized_ensemble_consistency.cell_matrix_relative_deviation > 0.0
    assert "quality.fixed_cell_consistency" in verdict.degraded_reasons

def test_stat0_verdict_round_trip() -> None:
    collection, catalog, controls, certificate, source_signature = _case(
        drift_ev_per_atom_ps=1.2e-3,
        degraded_controls=True,
    )
    verdict = assess_trajectory_quality(
        collection,
        energy_catalog=catalog,
        numerical_quality_controls=controls,
        simulation_control_certificate=certificate,
        source_identity_signature=source_signature,
        emit_warning=False,
    )
    rebuilt = TrajectoryQualityVerdict.from_dict(verdict.to_dict())
    assert rebuilt == verdict
    assert rebuilt.signature == verdict.signature


def test_stat0_public_exports() -> None:
    import mdstats

    assert mdstats.assess_trajectory_quality is assess_trajectory_quality
    assert "TrajectoryQualityVerdict" in mdstats.__all__
    assert "RealizedEnsembleConsistency" in mdstats.__all__
    assert "DiagnosticRequirement" in mdstats.__all__
    assert "assess_vasp_trajectory_quality" in mdstats.__all__
