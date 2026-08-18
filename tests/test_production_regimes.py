from __future__ import annotations

import numpy as np
import pytest

import mdstats
from mdstats.collection import AtomisticFrameCollection
from mdstats.io import (
    ChangePointStatus,
    EnsembleKind,
    ExternalBoundaryStatus,
    FrameEnergyCatalog,
    FrameEnergyChannel,
    InferenceStatus,
    NumericalMDQualityControls,
    ProductionCatalogStatus,
    ProductionIntervalStatus,
    ProductionRegimeCatalog,
    ProductionWindowPolicy,
    RegimeStationarityStatus,
    SimulationControlCertificate,
    SimulationControlComponent,
    ThermalizationEvidenceStatus,
    TrajectoryQualityOutcome,
    TrajectoryQualityPolicy,
    assess_production_regimes,
    assess_trajectory_quality,
)
from mdstats.provenance import FrameCollectionProvenance


def _component(kind: str, active: bool | None) -> SimulationControlComponent:
    return SimulationControlComponent(
        status=InferenceStatus.RESOLVED,
        kind=kind,
        active=active,
    )


def _certificate(source_signature: str) -> SimulationControlCertificate:
    return SimulationControlCertificate(
        source_identity_signature=source_signature,
        source_control_bundle_signature="b" * 64,
        run_controls_signature="c" * 64,
        policy_version="synthetic",
        dynamics_status=InferenceStatus.RESOLVED,
        dynamics_mode="molecular_dynamics",
        ensemble_status=InferenceStatus.RESOLVED,
        ensemble=EnsembleKind.NVE,
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


def _case(
    temperature: np.ndarray,
    *,
    total_drift_ev_per_atom_ps: float = 0.0,
) -> tuple[
    AtomisticFrameCollection,
    FrameEnergyCatalog,
    NumericalMDQualityControls,
    SimulationControlCertificate,
    str,
]:
    temperature = np.asarray(temperature, dtype=float)
    n_frames = temperature.size
    n_atoms = 2
    times = np.arange(n_frames, dtype=float) * 0.001
    dof = 3
    kinetic = 0.5 * dof * 8.617333262145e-5 * temperature
    rng = np.random.default_rng(144)
    total = (
        -10.0
        + total_drift_ev_per_atom_ps * n_atoms * times
        + rng.normal(0.0, 2.0e-6, n_frames)
    )
    potential = total - kinetic
    positions = np.zeros((n_frames, n_atoms, 3), dtype=float)
    positions[:, 1, 0] = 0.5
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
        potential_energies=potential,
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
            FrameEnergyChannel(
                "kinetic", "ionic_kinetic_energy", "eV", tuple(kinetic)
            ),
            FrameEnergyChannel(
                "e_fr_energy", "electronic_free_energy", "eV", tuple(potential)
            ),
            FrameEnergyChannel(
                "total", "source_reported_total_energy", "eV", tuple(total)
            ),
        ),
    )
    controls = NumericalMDQualityControls(
        potim_fs=1.0,
        requested_ionic_steps=n_frames,
        present_ionic_steps=n_frames,
        ionic_output_stride=1,
        ediff_ev=1.0e-7,
        nelm=100,
        nelmin=2,
        algo="Normal",
        ialgo=38,
        prec_explicit="Accurate",
        prec_effective="accura",
        lreal_explicit=False,
        lreal_effective=False,
        ropt=(),
        encut_ev=520.0,
        isym=0,
        scf_iteration_counts=(4,) * n_frames,
        scf_iteration_limit_reached=(False,) * n_frames,
        positions_complete=True,
        cells_complete=True,
        forces_complete=True,
        stresses_complete=False,
        native_velocity_frame_count=n_frames,
        energy_channel_completeness=(
            ("kinetic", 1.0),
            ("e_fr_energy", 1.0),
            ("total", 1.0),
        ),
    )
    source_signature = "a" * 64
    return collection, catalog, controls, _certificate(source_signature), source_signature


def _catalog(temperature: np.ndarray, **kwargs) -> ProductionRegimeCatalog:
    collection, energy, controls, certificate, source_signature = _case(
        temperature, **kwargs
    )
    quality = assess_trajectory_quality(
        collection,
        energy_catalog=energy,
        numerical_quality_controls=controls,
        simulation_control_certificate=certificate,
        source_identity_signature=source_signature,
        emit_warning=False,
        raise_on_unqualified=False,
    )
    return assess_production_regimes(
        collection,
        energy_catalog=energy,
        simulation_control_certificate=certificate,
        trajectory_quality_verdict=quality,
        source_identity_signature=source_signature,
    )


def test_stat1_stationary_full_source_is_scientific_candidate() -> None:
    rng = np.random.default_rng(3)
    catalog = _catalog(300.0 + rng.normal(0.0, 4.0, 512))
    assert catalog.overall_status is ProductionCatalogStatus.ACCEPTED
    assert catalog.change_points.status is ChangePointStatus.NONE
    assert catalog.selected_regime_ids == ("regime_000",)
    regime = catalog.regimes[0]
    assert regime.stationarity_status is RegimeStationarityStatus.SUPPORTED
    assert regime.production_interval_status is ProductionIntervalStatus.SCIENTIFIC_CANDIDATE
    assert regime.thermalization_status is ThermalizationEvidenceStatus.NO_DETECTED_TRANSIENT


def test_stat1_detects_heating_transient_and_keeps_later_regime() -> None:
    rng = np.random.default_rng(5)
    temperature = np.concatenate(
        [
            np.linspace(120.0, 300.0, 160),
            300.0 + rng.normal(0.0, 3.0, 480),
        ]
    )
    catalog = _catalog(temperature)
    assert catalog.change_points.status is ChangePointStatus.DETECTED
    assert catalog.change_points.frame_indices
    assert len(catalog.regimes) >= 2
    assert catalog.regimes[0].thermalization_status is ThermalizationEvidenceStatus.TRANSIENT_DETECTED
    assert any(regime.scientific_use_permitted for regime in catalog.regimes[1:])


def test_stat1_smooth_drift_is_not_promoted_as_stationary() -> None:
    temperature = np.linspace(250.0, 350.0, 512)
    catalog = _catalog(temperature)
    assert catalog.overall_status in {
        ProductionCatalogStatus.DIAGNOSTIC_ONLY,
        ProductionCatalogStatus.REJECTED,
    }
    assert not catalog.selected_regime_ids


def test_stat1_short_trajectory_is_insufficient_not_catastrophic() -> None:
    catalog = _catalog(np.linspace(295.0, 305.0, 64))
    assert catalog.overall_status is ProductionCatalogStatus.INSUFFICIENT
    assert catalog.regimes[0].stationarity_status is RegimeStationarityStatus.INSUFFICIENT


def test_stat1_external_boundaries_are_tested_not_trusted() -> None:
    rng = np.random.default_rng(7)
    temperature = 300.0 + rng.normal(0.0, 3.0, 512)
    collection, energy, controls, certificate, source_signature = _case(temperature)
    quality = assess_trajectory_quality(
        collection,
        energy_catalog=energy,
        numerical_quality_controls=controls,
        simulation_control_certificate=certificate,
        source_identity_signature=source_signature,
        emit_warning=False,
    )
    catalog = assess_production_regimes(
        collection,
        energy_catalog=energy,
        simulation_control_certificate=certificate,
        trajectory_quality_verdict=quality,
        source_identity_signature=source_signature,
        external_candidate_boundaries=(0, 256),
    )
    statuses = {item.frame_index: item.status for item in catalog.change_points.external_boundaries}
    assert statuses[0] is ExternalBoundaryStatus.SOURCE_EDGE
    assert statuses[256] in {ExternalBoundaryStatus.REJECTED, ExternalBoundaryStatus.INSUFFICIENT}


def test_stat1_catalog_round_trip_and_public_exports() -> None:
    rng = np.random.default_rng(11)
    catalog = _catalog(300.0 + rng.normal(0.0, 4.0, 512))
    rebuilt = ProductionRegimeCatalog.from_dict(catalog.to_dict())
    assert rebuilt == catalog
    assert rebuilt.signature == catalog.signature
    assert mdstats.assess_production_regimes is assess_production_regimes
    assert "ProductionRegimeCatalog" in mdstats.__all__


def test_stat0_uses_one_and_twenty_six_mev_drift_thresholds() -> None:
    policy = TrajectoryQualityPolicy()
    assert policy.strict_nve_drift_ev_per_atom_ps == pytest.approx(1.0e-3)
    assert policy.catastrophic_nve_drift_ev_per_atom_ps == pytest.approx(2.6e-2)
    assert policy.nve_hard_reference_temperature_kelvin == pytest.approx(300.0)
    assert policy.nve_hard_reference_time_ps == pytest.approx(1.0)

    collection, energy, controls, certificate, source_signature = _case(
        np.full(512, 300.0), total_drift_ev_per_atom_ps=3.0e-2
    )
    verdict = assess_trajectory_quality(
        collection,
        energy_catalog=energy,
        numerical_quality_controls=controls,
        simulation_control_certificate=certificate,
        source_identity_signature=source_signature,
        emit_warning=False,
        raise_on_unqualified=False,
    )
    assert verdict.outcome is TrajectoryQualityOutcome.UNQUALIFIED
    assert "quality.nve_energy_drift" in verdict.unqualified_reasons


def test_data1_refactor_preserves_frozen_stat1_catalog_signature() -> None:
    rng = np.random.default_rng(11)
    catalog = _catalog(300.0 + rng.normal(0.0, 4.0, 512))
    assert catalog.signature == "2fa818e194018e18db92fa76073de9919c25580e0ab253a27697e017c2210c8a"
