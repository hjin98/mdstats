from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import mdstats
from mdstats.analysis.site_samples import (
    EquilibriumStatus,
    PMFTemperatureProvenance,
    SamplingStateProvenance,
    StationarityStatus,
    prepare_framework_aligned_ion_sample_catalog,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    EvidenceState,
    ForceSourceProvenance,
    prepare_frame_registration,
    prepare_source_coordinate_contract,
)
from mdstats.io import (
    AdmissibilityStatus,
    ApproximationStatus,
    EnsembleApproximationProvenance,
    EnsembleKind,
    EvidenceAdmissibilityOverlay,
    EvidenceUse,
    FrameEnergyCatalog,
    FrameEnergyChannel,
    InferenceStatus,
    NumericalMDQualityControls,
    PmfAdmissibilityCertificate,
    ReweightingProvenance,
    ReweightingStatus,
    SimulationControlCertificate,
    SimulationControlComponent,
    SourceControlError,
    ThermodynamicMeasure,
    assess_pmf_admissibility,
    assess_production_regimes,
    assess_trajectory_quality,
    prepare_evidence_admissibility_overlay,
)
from mdstats.provenance import FrameCollectionProvenance


def _component(
    kind: str,
    active: bool | None,
    *,
    status: InferenceStatus = InferenceStatus.RESOLVED,
) -> SimulationControlComponent:
    return SimulationControlComponent(status=status, kind=kind, active=active)


def _certificate(
    source_signature: str,
    *,
    ensemble: EnsembleKind,
    bias_active: bool | None = False,
    constraints_active: bool | None = False,
) -> SimulationControlCertificate:
    thermostat_active = ensemble in {EnsembleKind.NVT, EnsembleKind.NPT}
    barostat_active = ensemble is EnsembleKind.NPT
    return SimulationControlCertificate(
        source_identity_signature=source_signature,
        source_control_bundle_signature="b" * 64,
        run_controls_signature="c" * 64,
        policy_version="synthetic-stat2",
        dynamics_status=InferenceStatus.RESOLVED,
        dynamics_mode="molecular_dynamics",
        ensemble_status=InferenceStatus.RESOLVED,
        ensemble=ensemble,
        propagator=_component("velocity_verlet", True),
        thermostat=_component(
            "langevin" if thermostat_active else "none", thermostat_active
        ),
        barostat=_component(
            "langevin_piston" if barostat_active else "none", barostat_active
        ),
        cell_control=_component(
            "variable_cell" if barostat_active else "fixed_cell", barostat_active
        ),
        bias=_component(
            "unknown" if bias_active is None else ("bias" if bias_active else "none"),
            bias_active,
            status=(
                InferenceStatus.UNRESOLVED
                if bias_active is None
                else InferenceStatus.RESOLVED
            ),
        ),
        constraints=_component(
            "unknown"
            if constraints_active is None
            else ("constraints" if constraints_active else "none"),
            constraints_active,
            status=(
                InferenceStatus.UNRESOLVED
                if constraints_active is None
                else InferenceStatus.RESOLVED
            ),
        ),
        force_provenance=_component("synthetic_physical_force", True),
        initial_velocity_provenance=_component("synthetic", True),
        continuation_provenance=_component("none", False),
        decisions=(),
    )


def _case(
    ensemble: EnsembleKind,
    *,
    n_frames: int = 512,
    bias_active: bool | None = False,
    constraints_active: bool | None = False,
):
    rng = np.random.default_rng(411)
    n_atoms = 2
    times = np.arange(n_frames, dtype=np.float64) * 0.001
    temperature = 300.0 + rng.normal(0.0, 3.0, n_frames)
    kinetic = 0.5 * 3.0 * 8.617333262145e-5 * temperature
    total = -10.0 + rng.normal(0.0, 2.0e-6, n_frames)
    potential = total - kinetic
    positions = np.zeros((n_frames, n_atoms, 3), dtype=np.float64)
    positions[:, 1, 0] = 0.5
    collection = AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.array([11, 11], dtype=np.int32),
        masses=np.array([22.99, 22.99]),
        pbc=np.ones(3, dtype=np.bool_),
        steps=np.arange(n_frames, dtype=np.int64),
        times=times,
        cells=np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=positions,
        velocities=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        forces=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
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
    energy = FrameEnergyCatalog(
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
    certificate = _certificate(
        source_signature,
        ensemble=ensemble,
        bias_active=bias_active,
        constraints_active=constraints_active,
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
    regimes = assess_production_regimes(
        collection,
        energy_catalog=energy,
        simulation_control_certificate=certificate,
        trajectory_quality_verdict=quality,
        source_identity_signature=source_signature,
    )
    return collection, certificate, quality, regimes, source_signature


def _admissibility(ensemble: EnsembleKind, **case_kwargs):
    collection, controls, quality, regimes, source = _case(
        ensemble, **case_kwargs
    )
    result = assess_pmf_admissibility(
        simulation_control_certificate=controls,
        trajectory_quality_verdict=quality,
        production_regime_catalog=regimes,
        source_identity_signature=source,
    )
    return collection, controls, quality, regimes, source, result


def test_nve_is_microcanonical_and_never_silently_canonical() -> None:
    _, _, _, _, _, result = _admissibility(EnsembleKind.NVE)
    regime = result.regime_admissibility[0]
    assert regime.permission(EvidenceUse.MICROCANONICAL_OCCUPANCY).status is AdmissibilityStatus.PERMITTED
    canonical = regime.permission(EvidenceUse.CANONICAL_LANDSCAPE)
    assert canonical.status is AdmissibilityStatus.BLOCKED
    assert canonical.measure is ThermodynamicMeasure.CANONICAL_HELMHOLTZ


def test_nvt_and_npt_have_distinct_direct_landscape_semantics() -> None:
    _, _, _, _, _, nvt = _admissibility(EnsembleKind.NVT)
    nvt_regime = nvt.regime_admissibility[0]
    assert nvt_regime.permission(EvidenceUse.CANONICAL_LANDSCAPE).status is AdmissibilityStatus.PERMITTED
    assert nvt_regime.permission(EvidenceUse.NPT_LANDSCAPE).status is AdmissibilityStatus.NOT_APPLICABLE

    _, _, _, _, _, npt = _admissibility(EnsembleKind.NPT)
    npt_permission = npt.regime_admissibility[0].permission(
        EvidenceUse.NPT_LANDSCAPE
    )
    assert npt_permission.status is AdmissibilityStatus.PERMITTED
    assert npt_permission.measure is ThermodynamicMeasure.ISOTHERMAL_ISOBARIC_GIBBS


def test_active_constraints_make_direct_nvt_landscape_conditional() -> None:
    _, _, _, _, _, result = _admissibility(
        EnsembleKind.NVT, constraints_active=True
    )
    permission = result.regime_admissibility[0].permission(
        EvidenceUse.CANONICAL_LANDSCAPE
    )
    assert permission.status is AdmissibilityStatus.CONDITIONAL


def test_active_constraints_make_nve_microcanonical_measure_conditional() -> None:
    _, _, _, _, _, result = _admissibility(
        EnsembleKind.NVE, constraints_active=True
    )
    permission = result.regime_admissibility[0].permission(
        EvidenceUse.MICROCANONICAL_OCCUPANCY
    )
    assert permission.status is AdmissibilityStatus.CONDITIONAL


def test_nve_canonical_promotion_requires_explicit_accepted_approximation() -> None:
    _, controls, quality, regimes, source, base = _admissibility(EnsembleKind.NVE)
    regime_id = base.regime_admissibility[0].regime_id
    approximation = EnsembleApproximationProvenance(
        source_identity_signature=source,
        status=ApproximationStatus.ACCEPTED,
        approximation_kind="ensemble_equivalence",
        target_temperature_kelvin=300.0,
        applicable_regime_ids=(regime_id,),
        evidence_signature="d" * 64,
    )
    result = assess_pmf_admissibility(
        simulation_control_certificate=controls,
        trajectory_quality_verdict=quality,
        production_regime_catalog=regimes,
        source_identity_signature=source,
        approximation_provenance=approximation,
    )
    permission = result.regime(regime_id).permission(
        EvidenceUse.CANONICAL_LANDSCAPE
    )
    assert permission.status is AdmissibilityStatus.CONDITIONAL
    assert permission.approximation_signature == approximation.signature


def test_nve_approximation_does_not_override_active_bias() -> None:
    _, controls, quality, regimes, source, base = _admissibility(
        EnsembleKind.NVE, bias_active=True
    )
    regime_id = base.regime_admissibility[0].regime_id
    approximation = EnsembleApproximationProvenance(
        source_identity_signature=source,
        status=ApproximationStatus.ACCEPTED,
        approximation_kind="finite_bath",
        target_temperature_kelvin=300.0,
        applicable_regime_ids=(regime_id,),
        evidence_signature="d" * 64,
    )
    result = assess_pmf_admissibility(
        simulation_control_certificate=controls,
        trajectory_quality_verdict=quality,
        production_regime_catalog=regimes,
        source_identity_signature=source,
        approximation_provenance=approximation,
    )
    assert (
        result.regime(regime_id)
        .permission(EvidenceUse.CANONICAL_LANDSCAPE)
        .status
        is AdmissibilityStatus.BLOCKED
    )


def test_verified_reweighting_is_regime_bound_and_replayable() -> None:
    _, controls, quality, regimes, source, base = _admissibility(EnsembleKind.NVE)
    regime_id = base.regime_admissibility[0].regime_id
    reweighting = ReweightingProvenance(
        source_identity_signature=source,
        status=ReweightingStatus.VERIFIED,
        method="normalized_importance_weights",
        target_measure="canonical_helmholtz",
        target_temperature_kelvin=300.0,
        applicable_regime_ids=(regime_id,),
        normalized_weights_available=True,
        finite_weight_diagnostics_passed=True,
        effective_sample_size=211.0,
        evidence_signature="e" * 64,
    )
    result = assess_pmf_admissibility(
        simulation_control_certificate=controls,
        trajectory_quality_verdict=quality,
        production_regime_catalog=regimes,
        source_identity_signature=source,
        reweighting_provenance=reweighting,
    )
    permission = result.regime(regime_id).permission(
        EvidenceUse.REWEIGHTED_LANDSCAPE
    )
    assert permission.status is AdmissibilityStatus.PERMITTED
    assert permission.reweighting_signature == reweighting.signature
    rebuilt = PmfAdmissibilityCertificate.from_dict(result.to_dict())
    assert rebuilt == result
    assert rebuilt.signature == result.signature


def test_unresolved_stationarity_keeps_only_diagnostic_spatial_evidence() -> None:
    _, controls, quality, regimes, source = _case(EnsembleKind.NVT, n_frames=64)
    result = assess_pmf_admissibility(
        simulation_control_certificate=controls,
        trajectory_quality_verdict=quality,
        production_regime_catalog=regimes,
        source_identity_signature=source,
    )
    regime = result.regime_admissibility[0]
    assert regime.permission(EvidenceUse.DESCRIPTIVE_DENSITY).status is AdmissibilityStatus.DIAGNOSTIC_ONLY
    assert regime.permission(EvidenceUse.CANONICAL_LANDSCAPE).status is AdmissibilityStatus.BLOCKED
    assert regime.permission(EvidenceUse.DIAGNOSTIC_ONLY).status is AdmissibilityStatus.PERMITTED


def test_cross_source_provenance_is_rejected() -> None:
    _, controls, quality, regimes, _ = _case(EnsembleKind.NVT)
    with pytest.raises(SourceControlError, match="source identity"):
        assess_pmf_admissibility(
            simulation_control_certificate=controls,
            trajectory_quality_verdict=quality,
            production_regime_catalog=regimes,
            source_identity_signature="f" * 64,
        )


def test_e0b_overlay_intersects_regime_and_raw_masks_and_persists_pmf_mask() -> None:
    collection, _, _, regimes, _, certificate = _admissibility(EnsembleKind.NVT)
    source_contract = prepare_source_coordinate_contract(
        collection,
        force_provenance=ForceSourceProvenance(
            physical_force_complete=EvidenceState.PRESENT,
            bias_or_constraint_force=EvidenceState.ABSENT,
            stochastic_or_thermostat_force=EvidenceState.ABSENT,
        ),
    )
    registration = prepare_frame_registration(
        collection, source_contract=source_contract
    )
    sample_catalog = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        sampling_state=SamplingStateProvenance(
            equilibrium_status=EquilibriumStatus.DECLARED_EQUILIBRIUM,
            stationarity_status=StationarityStatus.TESTED_STATIONARY,
            declaration_source="STAT2 focused test",
        ),
        pmf_temperature=PMFTemperatureProvenance.declared_constant(
            300.0, source="thermostat target"
        ),
        metadata={"source_identity_signature": "a" * 64},
    )
    regime_id = certificate.regime_admissibility[0].regime_id
    overlay = prepare_evidence_admissibility_overlay(
        sample_catalog,
        certificate=certificate,
        production_regime_catalog=regimes,
        regime_id=regime_id,
    )
    canonical = overlay.mask_for(EvidenceUse.CANONICAL_LANDSCAPE)
    np.testing.assert_array_equal(
        canonical, sample_catalog.evidence_masks.position_mask
    )
    np.testing.assert_array_equal(
        overlay.pmf_force_mask, sample_catalog.evidence_masks.joint_mask
    )
    assert not overlay.pmf_force_mask.flags.writeable
    rebuilt = EvidenceAdmissibilityOverlay.from_dict(overlay.to_dict())
    np.testing.assert_array_equal(rebuilt.pmf_force_mask, overlay.pmf_force_mask)
    assert rebuilt.signature == overlay.signature


def test_e0b_overlay_rejects_missing_or_cross_source_binding() -> None:
    collection, _, _, regimes, _, certificate = _admissibility(EnsembleKind.NVT)
    source_contract = prepare_source_coordinate_contract(
        collection,
        force_provenance=ForceSourceProvenance(
            physical_force_complete=EvidenceState.PRESENT,
            bias_or_constraint_force=EvidenceState.ABSENT,
            stochastic_or_thermostat_force=EvidenceState.ABSENT,
        ),
    )
    registration = prepare_frame_registration(
        collection, source_contract=source_contract
    )
    sample_catalog = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        metadata={"source_identity_signature": "f" * 64},
    )
    with pytest.raises(SourceControlError, match="another source"):
        prepare_evidence_admissibility_overlay(
            sample_catalog,
            certificate=certificate,
            production_regime_catalog=regimes,
            regime_id=certificate.regime_admissibility[0].regime_id,
        )


def test_stat2_public_exports_are_stable() -> None:
    assert mdstats.assess_pmf_admissibility is assess_pmf_admissibility
    assert mdstats.prepare_evidence_admissibility_overlay is prepare_evidence_admissibility_overlay
    assert "PmfAdmissibilityCertificate" in mdstats.__all__
