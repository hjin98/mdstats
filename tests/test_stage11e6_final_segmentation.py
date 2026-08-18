from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import (
    BoundaryInducedPolicy,
    FinalHystereticSegmentationCatalog,
    FinalMembershipClass,
    FinalMembershipSource,
    FinalPassageOutcome,
    FinalSegmentationInputError,
    FinalSegmentationOptions,
    FinalSegmentationResourceError,
    FinalSegmentationResourcePolicy,
    SegmentationStabilityStatus,
    prepare_final_hysteretic_segmentation,
)

from tests.test_stage11e4_temporal_assignment import _jitter, _run, _sample_catalog, _density_and_attractors
from mdstats.analysis.density import TemporalAssignmentOptions, prepare_provisional_temporal_assignment


VALIDATED = "d" * 64


def _final(xs, *, unknown_x=None, segment_starts=(), options=None):
    if segment_starts:
        catalog = _sample_catalog(xs, segment_starts=segment_starts)
        estimate, attractors = _density_and_attractors(catalog, unknown_x=unknown_x)
        temporal = prepare_provisional_temporal_assignment(
            catalog, estimate, attractors,
            options=TemporalAssignmentOptions(minimum_decorrelation_samples=6),
        )
    else:
        catalog, _estimate, _attractors, temporal = _run(xs, unknown_x=unknown_x)
    result = prepare_final_hysteretic_segmentation(
        catalog,
        SimpleNamespace(signature=VALIDATED),
        temporal,
        options=options or FinalSegmentationOptions(
            minimum_core_entry_frames=2,
            minimum_basin_exit_frames=2,
            sensitivity_thresholds=((2, 2),),
            sensitivity_stride_factors=(1,),
            minimum_events_for_stability=1,
        ),
    )
    return catalog, temporal, result


def test_one_jump_produces_final_residences_transition_and_occupancy_statistics():
    xs = np.r_[_jitter(0.2, 12), [0.35, 0.45, 0.55, 0.62], _jitter(0.7, 12)]
    catalog, temporal, result = _final(xs)
    assert result.membership.source_membership_signature == temporal.membership.signature
    assert len(result.residences) == 2
    counted = [p for p in result.passages if p.counted_transition]
    assert len(counted) == 1
    assert counted[0].outcome is FinalPassageOutcome.RESOLVED_TRANSITION
    assert (counted[0].source_state_id, counted[0].target_state_id) == (0, 1)
    assert result.residences[0].right_censored is False
    assert result.residences[1].right_censored is True
    assert np.all(result.assigned_state_ids[result.residences[0].sample_indices] == 0)
    assert np.all(result.assigned_state_ids[result.residences[1].sample_indices] == 1)
    stats = {item.state_id: item for item in result.state_statistics}
    assert stats[0].resolved_departure_count == 1
    assert stats[0].total_ion_time > 0.0
    assert 0.0 <= stats[0].vacancy_fraction_lower <= stats[0].vacancy_fraction_upper <= 1.0
    assert result.metadata["rates_deferred"] is True
    assert catalog.temporal_weighting.weight_units == result.metadata["weight_units"]


def test_short_exit_is_retained_by_core_basin_hysteresis_without_a_jump():
    xs = np.r_[_jitter(0.2, 8), [0.45], _jitter(0.2, 8)]
    _, _, result = _final(xs, options=FinalSegmentationOptions(
        minimum_core_entry_frames=2,
        minimum_basin_exit_frames=2,
        recrossing_window_frames=4,
        sensitivity_thresholds=((2, 2),),
        sensitivity_stride_factors=(1,),
        minimum_events_for_stability=1,
    ))
    assert len(result.residences) == 1
    assert any(p.outcome is FinalPassageOutcome.RETAINED_EXCURSION for p in result.passages)
    assert not any(p.counted_transition for p in result.passages)
    assert result.residences[0].retained_excursion_time > 0.0


def test_unsupported_gap_and_assignment_conflict_are_never_resolved_transitions():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.50, 0.60], _jitter(0.7, 8)]
    _, _, result = _final(xs, unknown_x=10)
    assert len(result.passages) == 1
    assert result.passages[0].outcome is FinalPassageOutcome.UNRESOLVED_GAP
    assert result.passages[0].contains_unknown
    assert not result.passages[0].counted_transition
    assert np.any(result.membership.membership_class == FinalMembershipClass.UNSUPPORTED_UNKNOWN)


def test_segment_resets_and_independent_ensembles_do_not_invent_events():
    xs = np.r_[_jitter(0.2, 8), _jitter(0.7, 8)]
    _, _, segmented = _final(xs, segment_starts=(8,))
    assert len(segmented.residences) == 2
    assert segmented.passages == ()
    assert {r.segment_id for r in segmented.residences} == {0, 1}

    catalog, estimate, attractors, temporal = _run([0.2, 0.2, 0.7, 0.7], semantics="ensemble")
    result = prepare_final_hysteretic_segmentation(
        catalog, SimpleNamespace(signature=VALIDATED), temporal,
        options=FinalSegmentationOptions(sensitivity_thresholds=((2, 2),), sensitivity_stride_factors=(1,)),
    )
    assert result.residences == () and result.passages == ()
    assert result.stability_status is SegmentationStabilityStatus.ENSEMBLE_UNAVAILABLE
    assert np.all(result.assigned_state_ids == -1)


def test_threshold_and_stride_stability_is_certified_only_with_event_support():
    xs = np.r_[
        _jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8),
        [0.60, 0.45], _jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8),
    ]
    _, _, result = _final(xs, options=FinalSegmentationOptions(
        minimum_core_entry_frames=1,
        minimum_basin_exit_frames=1,
        sensitivity_thresholds=((1, 1),),
        sensitivity_stride_factors=(1,),
        minimum_events_for_stability=2,
    ))
    assert result.stability_status is SegmentationStabilityStatus.STABLE
    assert len(result.sensitivity_records) == 1
    assert result.sensitivity_records[0].resolved_transition_count >= 2
    assert result.sensitivity_records[0].maximum_transition_relative_change == 0.0


def test_geometry_membership_requires_source_and_preserves_agreement_conflicts():
    xs = _jitter(0.2, 8)
    catalog, _estimate, _attractors, temporal = _run(xs)
    with pytest.raises(FinalSegmentationInputError, match="requires"):
        prepare_final_hysteretic_segmentation(
            catalog, SimpleNamespace(signature=VALIDATED), temporal,
            options=FinalSegmentationOptions(
                membership_source=FinalMembershipSource.SELECTED_GEOMETRY,
                sensitivity_thresholds=((2, 2),), sensitivity_stride_factors=(1,),
            ),
        )


def test_serialization_tamper_resources_options_and_public_api():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, temporal, result = _final(xs)
    replay = FinalHystereticSegmentationCatalog.from_dict(result.to_dict())
    assert replay.signature == result.signature
    payload = copy.deepcopy(result.to_dict())
    payload["assigned_state_ids"][0] = 99
    with pytest.raises(FinalSegmentationInputError):
        FinalHystereticSegmentationCatalog.from_dict(payload)
    with pytest.raises(FinalSegmentationResourceError):
        prepare_final_hysteretic_segmentation(
            catalog, SimpleNamespace(signature=VALIDATED), temporal,
            resources=FinalSegmentationResourcePolicy(max_samples=1),
        )
    with pytest.raises(FinalSegmentationInputError):
        FinalSegmentationOptions(sensitivity_stride_factors=(2,))
    assert mdstats.FINAL_SEGMENTATION_STAGE == "11E6"
    assert mdstats.prepare_final_hysteretic_segmentation is prepare_final_hysteretic_segmentation


def test_selected_geometry_boundary_policy_keeps_crossing_but_excludes_transition_count():
    from mdstats.analysis.density import AssignmentConflictRecord, AssignmentConflictStatus, RegionMembership
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, _estimate, _attractors, temporal = _run(xs)
    by_state = {0: [], 1: []}
    records = []
    for i, (raw, core, basin) in enumerate(zip(
        temporal.membership.raw_classification,
        temporal.membership.core_membership,
        temporal.membership.basin_membership,
        strict=True,
    )):
        state = int(core if core >= 0 else basin)
        if state >= 0:
            by_state[state].append((i, int(RegionMembership.CORE if core >= 0 else RegionMembership.BASIN)))
            status = AssignmentConflictStatus.UNIQUE_CORE if core >= 0 else AssignmentConflictStatus.UNIQUE_BASIN
            records.append(AssignmentConflictRecord(i, (), (), (), (), (state,), status))
        else:
            records.append(AssignmentConflictRecord(i, (), (), (), (), (), AssignmentConflictStatus.OUTSIDE_SUPPORTED_REGIONS))
    path_index = 8
    crossing = SimpleNamespace(
        sample_index_before=path_index,
        sample_index_after=path_index + 1,
        boundary_induced_crossing=True,
        drive_status=mdstats.CrossingDriveStatus.BOUNDARY_INDUCED,
    )
    refinements = []
    for state in (0, 1):
        pairs = by_state[state]
        refinements.append(SimpleNamespace(
            state_id=state,
            sample_indices=np.asarray([p[0] for p in pairs], dtype=np.int64),
            selected_membership=np.asarray([p[1] for p in pairs], dtype=np.int64),
            crossings=(crossing,) if state == 0 else (),
        ))
    geometry = SimpleNamespace(
        signature="g" * 64,
        validated_frozen_catalog_signature=VALIDATED,
        refinements=tuple(refinements),
        assignment_conflicts=tuple(records),
    )
    result = prepare_final_hysteretic_segmentation(
        catalog, SimpleNamespace(signature=VALIDATED), temporal,
        geometry_catalog=geometry,
        options=FinalSegmentationOptions(
            membership_source=FinalMembershipSource.SELECTED_GEOMETRY,
            boundary_induced_policy=BoundaryInducedPolicy.MARK_UNRESOLVED,
            minimum_core_entry_frames=2,
            minimum_basin_exit_frames=1,
            sensitivity_thresholds=((2, 1),),
            sensitivity_stride_factors=(1,),
            minimum_events_for_stability=1,
        ),
    )
    assert any(p.boundary_induced for p in result.passages)
    passage = next(p for p in result.passages if p.boundary_induced)
    assert passage.outcome is FinalPassageOutcome.BOUNDARY_INDUCED
    assert not passage.counted_transition
