from __future__ import annotations

import copy
from dataclasses import replace

import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import (
    EvidenceBlockPlan,
    FinalSegmentationOptions,
    ObservedNetworkInputError,
    ObservedNetworkModelCatalog,
    ObservedNetworkOptions,
    ObservedNetworkResourceError,
    ObservedNetworkResourcePolicy,
    StructuralEdgeComparisonStatus,
    StructuralNetworkEdge,
    TransferApplicationKind,
    TransferDomainMetadata,
    TransferValidationStatus,
    apply_observed_network_model,
    attach_transfer_applications,
    prepare_final_hysteretic_segmentation,
    prepare_observed_network_model,
    prepare_observed_transition_paths,
    prepare_validated_frozen_catalog,
)
from tests.test_stage11e5_joint_evidence_validation import _two_state


def _pipeline(*, structural_edges=(), semantic=True, options=None, resources=None):
    catalog, estimate, attractors, temporal, structural = _two_state()
    frames = tuple(int(v) for v in np.unique(catalog.frame_indices))
    validated = prepare_validated_frozen_catalog(
        catalog,
        estimate,
        attractors,
        temporal,
        structural,
        block_plan=EvidenceBlockPlan.discovery_only(frames),
    )
    final = prepare_final_hysteretic_segmentation(
        catalog,
        validated,
        temporal,
        options=FinalSegmentationOptions(
            minimum_core_entry_frames=1,
            minimum_basin_exit_frames=1,
            sensitivity_thresholds=((1, 1),),
            sensitivity_stride_factors=(1,),
            minimum_events_for_stability=1,
        ),
    )
    paths = prepare_observed_transition_paths(catalog, final)
    labels = {(0, 0): "left_ring_state", (0, 1): "right_ring_state"} if semantic else None
    model = prepare_observed_network_model(
        validated,
        paths,
        structural_edges=structural_edges,
        semantic_class_labels=labels,
        options=options,
        resources=resources,
    )
    return catalog, validated, final, paths, model


def _domain(catalog, *, registration_signature=None, kind=TransferApplicationKind.UNTOUCHED_FINAL_VALIDATION):
    return TransferDomainMetadata(
        domain_id="held_out_trajectory",
        application_kind=kind,
        species=catalog.species_label,
        coordinate_frame="registered_fractional",
        length_units="dimensionless",
        registration_signature=catalog.registration_signature if registration_signature is None else registration_signature,
        registration_group_signature=None,
        analysis_metric_covariant=np.eye(3),
        temperature=300.0,
        composition="synthetic_two_state",
    )


def test_observed_network_keeps_state_instances_complexes_classes_and_models_distinct():
    _catalog, validated, _final, paths, model = _pipeline()
    assert len(model.nodes) == len(validated.states) == 2
    assert [node.node_id for node in model.nodes] == [0, 1]
    assert [node.canonical_state_id for node in model.nodes] == [0, 1]
    assert len(model.site_complexes) == 2
    assert len(model.semantic_classes) == 2
    assert len(model.compact_models) == 2
    assert all(item.member_node_ids.size == 1 for item in model.compact_models)
    assert model.metadata["state_instances_merged"] is False
    assert model.metadata["rates_inferred"] is False
    assert model.transition_path_catalog_signature == paths.signature


def test_structural_and_observed_edges_are_compared_without_inventing_connections():
    observed = StructuralNetworkEdge(0, 1, np.zeros(3, dtype=np.int64), "window:0")
    unobserved = StructuralNetworkEdge(1, 0, np.zeros(3, dtype=np.int64), "window:0")
    _catalog, _validated, _final, _paths, model = _pipeline(structural_edges=(observed, unobserved))
    assert len(model.observed_edges) == 1
    assert model.observed_edges[0].structural_comparison is StructuralEdgeComparisonStatus.OBSERVED_AND_STRUCTURAL
    assert model.observed_edges[0].structural_edge_signatures == (observed.signature,)
    assert model.unobserved_structural_edges == (unobserved,)
    assert model.metadata["structural_edges_create_observed_edges"] is False


def test_observed_off_structural_edge_remains_explicit():
    unrelated = StructuralNetworkEdge(1, 0, np.zeros(3, dtype=np.int64), "window:reverse")
    _catalog, _validated, _final, _paths, model = _pipeline(structural_edges=(unrelated,))
    edge = model.observed_edges[0]
    assert edge.structural_comparison is StructuralEdgeComparisonStatus.OBSERVED_OFF_STRUCTURAL_NETWORK
    assert model.metadata["observed_off_structural_edge_count"] == 1


def test_untouched_transfer_reproduces_catalog_with_periodic_and_ambiguous_samples():
    catalog, _validated, _final, _paths, model = _pipeline()
    positions = np.asarray([[0.20, 0.0, 0.0], [0.70, 0.0, 0.0], [0.95, 0.0, 0.0]])
    result = apply_observed_network_model(
        model,
        positions,
        _domain(catalog),
        reference_state_ids=np.asarray([0, 1, -1], dtype=np.int32),
        observed_transition_edges=((0, 1, 0, 0, 0),),
    )
    assert np.array_equal(result.assigned_state_ids[:2], [0, 1])
    assert result.ambiguity_mask[2]
    assert result.status is TransferValidationStatus.REPRODUCED_WITHIN_UNCERTAINTY
    assert result.mismatch_fraction == pytest.approx(0.0)
    attached = attach_transfer_applications(model, (result,))
    assert len(attached.transfer_applications) == 1
    assert attached.model_basis_signature == model.model_basis_signature
    assert attached.signature != model.signature


def test_external_transfer_off_network_and_failed_assignment_remain_explicit():
    catalog, _validated, _final, _paths, model = _pipeline()
    off = apply_observed_network_model(
        model,
        np.asarray([[0.20, 0.0, 0.0], [0.70, 0.0, 0.0]]),
        _domain(catalog, kind=TransferApplicationKind.EXTERNAL_TRANSFER),
        reference_state_ids=np.asarray([0, 1], dtype=np.int32),
        observed_transition_edges=((1, 0, 1, 0, 0),),
    )
    assert off.status is TransferValidationStatus.OFF_NETWORK_EVENTS
    assert off.off_network_transition_edges.shape == (1, 5)
    failed = apply_observed_network_model(
        model,
        np.asarray([[0.70, 0.0, 0.0], [0.20, 0.0, 0.0]]),
        _domain(catalog, kind=TransferApplicationKind.EXTERNAL_TRANSFER),
        reference_state_ids=np.asarray([0, 1], dtype=np.int32),
        mismatch_tolerance=0.1,
    )
    assert failed.status is TransferValidationStatus.FAILED_TRANSFER
    assert failed.mismatch_fraction == pytest.approx(1.0)


def test_transfer_domain_mismatch_is_fail_closed():
    catalog, _validated, _final, _paths, model = _pipeline()
    result = apply_observed_network_model(
        model,
        np.asarray([[0.20, 0.0, 0.0]]),
        _domain(catalog, registration_signature="f" * 64),
        reference_state_ids=np.asarray([0], dtype=np.int32),
    )
    assert result.status is TransferValidationStatus.DOMAIN_MISMATCH
    assert result.assigned_state_ids[0] == -1
    assert result.outside_domain_mask[0]


def test_serialization_tamper_source_binding_and_resources():
    catalog, validated, _final, paths, model = _pipeline()
    replay = ObservedNetworkModelCatalog.from_dict(model.to_dict())
    assert replay.signature == model.signature
    payload = copy.deepcopy(model.to_dict())
    payload["nodes"][0]["canonical_state_id"] = 99
    with pytest.raises(ObservedNetworkInputError):
        ObservedNetworkModelCatalog.from_dict(payload)
    with pytest.raises(ObservedNetworkInputError, match="another sample catalog"):
        prepare_observed_network_model(replace(validated, sample_catalog_signature="a" * 64, signature=""), paths)
    with pytest.raises(ObservedNetworkResourceError, match="state instances"):
        prepare_observed_network_model(validated, paths, resources=ObservedNetworkResourcePolicy(max_state_instances=1))
    limited_model = replace(
        model,
        resources=ObservedNetworkResourcePolicy(max_transfer_samples=1),
        signature="",
    )
    with pytest.raises(ObservedNetworkResourceError, match="transfer samples"):
        apply_observed_network_model(limited_model, np.zeros((2, 3)), _domain(catalog))


def test_public_exports_and_stage_boundary():
    assert mdstats.OBSERVED_NETWORK_STAGE == "11E7"
    assert mdstats.prepare_observed_network_model is prepare_observed_network_model
    assert mdstats.apply_observed_network_model is apply_observed_network_model
    assert "ObservedNetworkModelCatalog" in mdstats.__all__
