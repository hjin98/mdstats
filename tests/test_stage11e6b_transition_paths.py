from __future__ import annotations

import copy
from dataclasses import replace

import numpy as np
import pytest

import mdstats
from mdstats.analysis.density.transition_paths import (
    CollectiveEventStatus,
    FirstHitResolutionStatus,
    ObservedTransitionPathCatalog,
    PathEnsembleStatus,
    PathEvidenceStatus,
    RegistrationCompatibilityClass,
    TransitionPathEvidenceTable,
    TransitionPathInputError,
    TransitionPathOptions,
    TransitionPathResourceError,
    TransitionPathResourcePolicy,
    prepare_observed_transition_paths,
    prepare_registration_compatibility_class,
)
from mdstats.analysis.density import FinalSegmentationOptions
from tests.test_stage11e4_temporal_assignment import _jitter, _run
from tests.test_stage11e6_final_segmentation import _final


def _paths(xs, *, unknown_x=None, options=None, evidence=None):
    catalog, _temporal, final = _final(
        xs,
        unknown_x=unknown_x,
        options=FinalSegmentationOptions(
            minimum_core_entry_frames=1,
            minimum_basin_exit_frames=1,
            sensitivity_thresholds=((1, 1),),
            sensitivity_stride_factors=(1,),
            minimum_events_for_stability=1,
        ),
    )
    return catalog, final, prepare_observed_transition_paths(
        catalog, final, evidence_tables=evidence, options=options
    )


def test_one_jump_is_one_observed_connection_but_not_a_rate_or_representative_ensemble():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, final, paths = _paths(xs)
    successful = [event for event in paths.events if event.successful_connection]
    assert len(successful) == 1
    event = successful[0]
    assert event.first_hit_status is FirstHitResolutionStatus.RESOLVED_FIRST_HIT
    assert event.sample_catalog_signature == catalog.signature
    assert event.final_segmentation_signature == final.signature
    assert event.source_exit_bracket.size == 2
    assert event.target_entry_bracket.size == 2
    assert not event.metadata["interpolation_used"]
    assert len(paths.ensembles) == 1
    assert paths.ensembles[0].status is PathEnsembleStatus.SINGLE_OBSERVED_PATH
    assert paths.metadata["rates_deferred"] is True
    assert paths.ensembles[0].metadata["representative_path_claimed"] is False


def test_repeated_paths_keep_physical_time_image_translation_and_resolve_only_with_support():
    xs = np.r_[
        _jitter(0.2, 6), [0.45, 0.60], _jitter(0.7, 6),
        [0.60, 0.45], _jitter(0.2, 6), [0.45, 0.60], _jitter(0.7, 6),
        [0.60, 0.45], _jitter(0.2, 6), [0.45, 0.60], _jitter(0.7, 6),
    ]
    catalog, final, _ = _paths(xs)
    shifts = np.zeros_like(catalog.registered_image_shifts)
    shifts[catalog.frame_indices >= catalog.frame_indices.max() // 2, 0] = 1
    shifted = replace(catalog, registered_image_shifts=shifts, signature="")
    rebound = replace(final, sample_catalog_signature=shifted.signature, membership=replace(
        final.membership, sample_catalog_signature=shifted.signature, signature=""
    ), signature="")
    paths = prepare_observed_transition_paths(
        shifted,
        rebound,
        options=TransitionPathOptions(minimum_paths_for_resolved_ensemble=3),
    )
    forward = [event for event in paths.events if event.successful_connection and event.source_state_id == 0]
    assert len(forward) >= 3
    assert all(event.path_times is not None for event in forward)
    assert any(np.array_equal(event.periodic_translation, [1, 0, 0]) for event in forward)
    ensemble = next(item for item in paths.ensembles if item.source_state_id == 0 and item.target_state_id == 1
                    and np.array_equal(item.periodic_translation, [0, 0, 0]))
    assert ensemble.status in {PathEnsembleStatus.PATH_ENSEMBLE_UNDERSAMPLED, PathEnsembleStatus.PATH_ENSEMBLE_RESOLVED}


def test_gap_interrupted_and_failed_excursions_are_retained_but_never_pooled():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.50, 0.60], _jitter(0.7, 8)]
    _, _, paths = _paths(xs, unknown_x=10)
    assert len(paths.events) == 1
    assert paths.events[0].first_hit_status is FirstHitResolutionStatus.GAP_INTERRUPTED
    assert paths.events[0].contains_unknown
    assert not paths.events[0].successful_connection
    assert paths.ensembles == ()


def test_structural_coordination_harmonic_force_and_density_evidence_are_retained_exactly():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, _temporal, final = _final(
        xs,
        options=FinalSegmentationOptions(
            minimum_core_entry_frames=1,
            minimum_basin_exit_frames=1,
            sensitivity_thresholds=((1, 1),), sensitivity_stride_factors=(1,), minimum_events_for_stability=1,
        ),
    )
    n = catalog.n_samples
    table = TransitionPathEvidenceTable(
        sample_catalog_signature=catalog.signature,
        sample_indices=np.arange(n),
        ring_ids=np.full(n, 7),
        ring_sector_ids=np.arange(n, dtype=np.int32) % 6,
        feature_names=("M-O1", "M-O2"),
        coordination_values=np.column_stack([np.linspace(2.0, 2.5, n), np.linspace(2.2, 2.7, n)]),
        harmonic_names=("m1", "m3"),
        harmonic_amplitudes=np.column_stack([np.linspace(0.0, 1.0, n), np.ones(n)]),
        harmonic_phases=np.zeros((n, 2)),
        apertures=np.linspace(3.0, 3.2, n),
        puckering=np.linspace(0.1, 0.2, n),
        local_occupancy=np.ones(n),
        density_values=np.linspace(0.5, 0.1, n),
        pmf_values=np.linspace(0.0, 0.8, n),
    )
    paths = prepare_observed_transition_paths(catalog, final, evidence_tables=table)
    event = next(v for v in paths.events if v.successful_connection)
    assert event.evidence_status is PathEvidenceStatus.COMPLETE
    assert event.primary_structural_id == 7 and not event.structural_ambiguity
    assert event.feature_names == ("M-O1", "M-O2")
    assert event.coordination_values.shape == (event.sample_indices.size, 2)
    assert event.minimum_density == pytest.approx(np.min(event.density_values))
    assert event.maximum_pmf == pytest.approx(np.max(event.pmf_values))
    assert np.array_equal(event.force_available_mask, np.zeros(event.sample_indices.size, dtype=bool))


def test_registration_compatibility_pools_distinct_registration_signatures_only_with_shared_group():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    c1, _t1, f1 = _final(xs, options=FinalSegmentationOptions(
        minimum_core_entry_frames=1, minimum_basin_exit_frames=1,
        sensitivity_thresholds=((1, 1),), sensitivity_stride_factors=(1,), minimum_events_for_stability=1))
    group = "a" * 64
    c1g = replace(c1, registration_group_signature=group, registration_group_member_index=0, signature="")
    f1g = replace(f1, sample_catalog_signature=c1g.signature,
                  membership=replace(f1.membership, sample_catalog_signature=c1g.signature, signature=""), signature="")
    c2 = replace(c1, registration_signature="b" * 64, registration_group_signature=group,
                 registration_group_member_index=1,
                 force_provenance=replace(c1.force_provenance, registration_signature="b" * 64, signature=""), signature="")
    f2 = replace(f1, sample_catalog_signature=c2.signature,
                 membership=replace(f1.membership, sample_catalog_signature=c2.signature, signature=""), signature="")
    compatibility = prepare_registration_compatibility_class(
        (c1g, c2), state_correspondence=((0, 0, 10), (0, 1, 11), (1, 0, 10), (1, 1, 11))
    )
    paths = prepare_observed_transition_paths((c1g, c2), (f1g, f2), registration_compatibility=compatibility)
    assert len(paths.events) == 2
    assert len(paths.ensembles) == 1
    assert (paths.ensembles[0].source_state_id, paths.ensembles[0].target_state_id) == (10, 11)
    with pytest.raises(TransitionPathInputError, match="shared registration group"):
        prepare_registration_compatibility_class((replace(c1g, registration_group_signature=None,
                                                            registration_group_member_index=None, signature=""),
                                                   replace(c2, registration_group_signature=None,
                                                           registration_group_member_index=None, signature="")))


def test_concurrent_opposite_events_are_candidate_exchange_without_many_body_model_claim():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, final, paths = _paths(xs)
    event = paths.events[0]
    from mdstats.analysis.density.transition_paths import _classify_collective
    opposite = replace(
        event,
        event_id=1,
        atom_index=event.atom_index + 1,
        source_state_id=event.target_state_id,
        target_state_id=event.source_state_id,
        candidate_target_state_ids=np.asarray([event.source_state_id], dtype=np.int32),
        signature="",
    )
    classified = _classify_collective([event, opposite], 0)
    assert all(v.collective_status is CollectiveEventStatus.CANDIDATE_EXCHANGE for v in classified)
    assert np.array_equal(classified[0].concurrent_event_ids, [1])



def test_multiple_target_candidates_remain_explicit_and_are_not_promoted_to_a_connection():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, _temporal, final = _final(
        xs,
        options=FinalSegmentationOptions(
            minimum_core_entry_frames=1, minimum_basin_exit_frames=1,
            sensitivity_thresholds=((1, 1),), sensitivity_stride_factors=(1,), minimum_events_for_stability=1,
        ),
    )
    paths = prepare_observed_transition_paths(
        catalog, final, first_hit_candidate_states={0: (1, 2)}
    )
    event = paths.events[0]
    assert event.first_hit_status is FirstHitResolutionStatus.MULTIPLE_TARGETS_BETWEEN_FRAMES
    assert np.array_equal(event.candidate_target_state_ids, [1, 2])
    assert not event.successful_connection
    assert paths.ensembles == ()

def test_serialization_tamper_resources_options_and_public_api():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, final, paths = _paths(xs)
    replay = ObservedTransitionPathCatalog.from_dict(paths.to_dict())
    assert replay.signature == paths.signature
    payload = copy.deepcopy(paths.to_dict())
    payload["events"][0]["periodic_translation"][0] += 1
    with pytest.raises(TransitionPathInputError):
        ObservedTransitionPathCatalog.from_dict(payload)
    with pytest.raises(TransitionPathResourceError):
        prepare_observed_transition_paths(catalog, final, resources=TransitionPathResourcePolicy(max_events=1, max_path_samples=1))
    with pytest.raises(TransitionPathInputError):
        TransitionPathOptions(clustering_resample_points=1)
    assert mdstats.TRANSITION_PATH_STAGE == "11E6b"
    assert mdstats.prepare_observed_transition_paths is prepare_observed_transition_paths
