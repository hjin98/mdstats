from __future__ import annotations

import copy
import math

import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import StructuralObjectKind
from mdstats.analysis.density.coordination_fingerprints import (
    CoordinationFingerprintCatalog,
    CoordinationFingerprintInputError,
    CoordinationFingerprintOptions,
    CoordinationFingerprintResourcePolicy,
    CoordinationStructuralClass,
    OccupancyMixtureStatus,
    analyze_coordination_fingerprint_samples,
)


def _ring(k=6, radius=2.5, serration=0.0):
    theta = np.arange(k) * 2.0 * np.pi / k
    radii = radius + serration * ((-1.0) ** np.arange(k))
    oxygen = np.column_stack((radii * np.cos(theta), radii * np.sin(theta), np.zeros(k)))
    t_theta = theta + np.pi / k
    t = np.column_stack(((radius + 0.8) * np.cos(t_theta), (radius + 0.8) * np.sin(t_theta), np.zeros(k)))
    edges = np.linalg.norm(np.roll(oxygen, -1, axis=0) - oxygen, axis=1)
    arc = 0.5 * (np.roll(edges, 1) + edges)
    return oxygen, t, theta, arc


def _result(local, *, serration=0.0, labels=None, predicted_local=None, options=None):
    local = np.asarray(local, dtype=float)
    oxygen, t, angles, arc = _ring(serration=serration)
    mo = np.linalg.norm(oxygen[None, :, :] - local[:, None, :], axis=2)
    mt = np.linalg.norm(t[None, :, :] - local[:, None, :], axis=2)
    centered_points = np.column_stack((np.zeros(len(local)), np.zeros(len(local)), local[:, 2]))
    centered = np.linalg.norm(oxygen[None, :, :] - centered_points[:, None, :], axis=2)
    if predicted_local is None:
        predicted_local = np.average(local, axis=0)
    predicted = np.repeat(np.linalg.norm(oxygen - np.asarray(predicted_local), axis=1)[None, :], len(local), axis=0)
    n = len(local)
    return analyze_coordination_fingerprint_samples(
        state_id=0,
        candidate_index=0,
        persistent_identity="ring:synthetic-s6r",
        structural_object_kind=StructuralObjectKind.RING,
        sample_indices=np.arange(n),
        frame_indices=np.arange(n),
        ion_atom_indices=np.zeros(n, dtype=int),
        represented_time_weights=np.ones(n),
        local_coordinates=local,
        mo_distances=mo,
        mt_distances=mt,
        centered_reference_mo_distances=centered,
        geometry_predicted_mo_distances=predicted,
        oxygen_atom_indices=tuple(range(1, 7)),
        oxygen_image_shifts=((0, 0, 0),) * 6,
        oxygen_environment_signatures=("Si-Al",) * 6,
        oxygen_aliases=(None,) * 6,
        t_atom_indices=tuple(range(7, 13)),
        t_image_shifts=((0, 0, 0),) * 6,
        mean_oxygen_angles=angles,
        mean_oxygen_arc_weights=arc,
        occupancy_labels=labels,
        options=options,
    )


def test_centered_serrated_s6r_is_not_misclassified_as_off_center():
    rng = np.random.default_rng(4)
    local = rng.normal(scale=0.015, size=(40, 3))
    local[:, 2] *= 0.2
    result = _result(local, serration=0.18)
    assert result.classification.structural_class is CoordinationStructuralClass.POINT
    spectrum = result.spectrum("M-O mean distance")
    assert spectrum.mode(3).amplitude > spectrum.mode(1).amplitude
    assert result.classification.direct_mean_radial_offset < 0.15


def test_coherent_off_center_geometry_matches_forward_model():
    rng = np.random.default_rng(5)
    local = np.array([0.42, 0.04, 0.08]) + rng.normal(scale=0.008, size=(50, 3))
    result = _result(local, serration=0.12)
    assert result.classification.structural_class is CoordinationStructuralClass.DISCRETE_OFF_CENTER
    assert result.classification.phase_resolved
    assert result.classification.geometry_explained_fraction > 0.95
    assert result.classification.forward_model_residual_rms < 0.02


def test_residual_spectrum_is_explicitly_diagnostic_not_component_separation():
    local = np.repeat([[0.35, 0.0, 0.0]], 12, axis=0)
    result = _result(local, serration=0.2)
    residual = result.spectrum("M-O centered-reference residual")
    assert residual.diagnostic_only is True
    assert "residual_spectra_are_diagnostic_not_exact_component_separation" in result.classification.diagnostics


def test_phase_dependent_discrete_label_requires_stable_circular_phase():
    theta = np.linspace(0.0, 2.0 * np.pi, 48, endpoint=False)
    local = np.column_stack((0.4 * np.cos(theta), 0.4 * np.sin(theta), np.zeros_like(theta)))
    result = _result(local)
    assert not result.classification.phase_resolved
    assert result.classification.structural_class is not CoordinationStructuralClass.DISCRETE_OFF_CENTER
    assert result.classification.annularity_score > 0.5


def test_occupancy_conditioned_mixture_remains_explicit():
    rng = np.random.default_rng(6)
    left = np.array([-0.36, 0.0, 0.0]) + rng.normal(scale=0.01, size=(20, 3))
    right = np.array([0.36, 0.0, 0.0]) + rng.normal(scale=0.01, size=(20, 3))
    result = _result(np.vstack((left, right)), labels=("vacant-neighbor",) * 20 + ("occupied-neighbor",) * 20)
    assert result.classification.occupancy_mixture_status is OccupancyMixtureStatus.RESOLVED_MIXTURE
    assert len(result.occupancy_contexts) == 2
    assert "occupancy_conditioned_fingerprint_mixture_retained" in result.classification.diagnostics


def test_rank_safe_actual_angle_fit_reports_rank_without_forcing_modes():
    options = CoordinationFingerprintOptions(maximum_harmonic_mode=4)
    result = _result(np.repeat([[0.25, 0.0, 0.0]], 10, axis=0), options=options)
    fit = result.spectrum("M-O mean distance", "rank_safe_actual_angle_least_squares")
    assert fit.fit_rank is not None
    assert fit.parameter_count == 7
    assert fit.fit_rank < fit.parameter_count
    assert fit.harmonics == ()


def test_multiple_plausible_associations_and_serialization_remain_separate():
    first = _result(np.repeat([[0.2, 0.0, 0.0]], 8, axis=0))
    second = _result(np.repeat([[-0.2, 0.0, 0.0]], 8, axis=0))
    second = type(second)(
        state_id=0,
        candidate_index=1,
        status=second.status,
        structural_object_kind=second.structural_object_kind,
        persistent_identity="ring:second",
        sample_indices=second.sample_indices,
        frame_indices=second.frame_indices,
        ion_atom_indices=second.ion_atom_indices,
        represented_time_weights=second.represented_time_weights,
        local_coordinates=second.local_coordinates,
        mo_distances=second.mo_distances,
        mt_distances=second.mt_distances,
        centered_reference_mo_distances=second.centered_reference_mo_distances,
        geometry_predicted_mo_distances=second.geometry_predicted_mo_distances,
        oxygen_atom_indices=second.oxygen_atom_indices,
        oxygen_image_shifts=second.oxygen_image_shifts,
        oxygen_environment_signatures=second.oxygen_environment_signatures,
        oxygen_aliases=second.oxygen_aliases,
        t_atom_indices=second.t_atom_indices,
        t_image_shifts=second.t_image_shifts,
        spectra=second.spectra,
        occupancy_contexts=second.occupancy_contexts,
        classification=second.classification,
    )
    catalog = CoordinationFingerprintCatalog(
        "a" * 64, "b" * 64, "c" * 64, "d" * 64, "e" * 64, "f" * 64,
        CoordinationFingerprintOptions(), CoordinationFingerprintResourcePolicy(), (first, second),
        {"multiple_structural_associations_retained": True},
    )
    replay = CoordinationFingerprintCatalog.from_dict(catalog.to_dict())
    assert replay.signature == catalog.signature
    assert len(replay.for_state(0)) == 2
    payload = copy.deepcopy(catalog.to_dict())
    payload["fingerprints"][0]["local_coordinates"][0][0] += 0.1
    with pytest.raises(CoordinationFingerprintInputError):
        CoordinationFingerprintCatalog.from_dict(payload)


def test_public_api_stage_and_resource_validation():
    assert mdstats.COORDINATION_FINGERPRINT_STAGE == "11E5a"
    with pytest.raises(CoordinationFingerprintInputError):
        CoordinationFingerprintOptions(phase_stability_threshold=1.1)
    with pytest.raises(CoordinationFingerprintInputError):
        CoordinationFingerprintResourcePolicy(max_states=0)
