from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import mdstats
from mdstats.analysis.site_samples import prepare_framework_aligned_ion_sample_catalog
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import prepare_frame_registration, prepare_source_coordinate_contract
from mdstats.io import (
    ChangePointCatalog,
    ChangePointStatus,
    CrossfitDomain,
    CrossfitPartitionMode,
    CrossfitPartitionStatus,
    EvidenceCrossfitPartition,
    EvidenceCrossfitPolicy,
    FeatureCorrespondencePolicy,
    FeatureType,
    ProductionCatalogStatus,
    ProductionIntervalStatus,
    ProductionRegime,
    ProductionRegimeCatalog,
    QualityDiagnosticBlockPartition,
    RegimeStationarityStatus,
    SamplingAdequacyPolicy,
    SelectionConditioningStatus,
    SourceControlError,
    ThermalizationEvidenceStatus,
    TrajectoryQualityOutcome,
    build_evidence_crossfit_partition,
)
from mdstats.provenance import FrameCollectionProvenance


SOURCE = "a" * 64


def _collection(n_frames: int = 192) -> AtomisticFrameCollection:
    t = np.arange(n_frames, dtype=np.float64) * 0.001
    frac = np.zeros((n_frames, 2, 3), dtype=np.float64)
    frac[:, 0, 0] = 0.20 + 0.02 * np.sin(2.0 * np.pi * np.arange(n_frames) / 17.0)
    frac[:, 1, 0] = 0.70 + 0.02 * np.cos(2.0 * np.pi * np.arange(n_frames) / 19.0)
    frac[:, :, 1] = np.array([0.25, 0.75])[None, :]
    frac[:, :, 2] = np.array([0.30, 0.60])[None, :]
    return AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(1000, 1000 + n_frames, dtype=np.int64),
        atomic_numbers=np.array([11, 11], dtype=np.int32),
        masses=np.array([22.98976928, 22.98976928]),
        pbc=np.ones(3, dtype=np.bool_),
        steps=np.arange(n_frames, dtype=np.int64),
        times=t,
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=frac,
        velocities=np.zeros_like(frac),
        forces=np.zeros_like(frac),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="internal",
        ),
    )


def _sample_catalog(n_frames: int = 192, *, source: str = SOURCE):
    collection = _collection(n_frames)
    contract = prepare_source_coordinate_contract(collection)
    registration = prepare_frame_registration(collection, source_contract=contract)
    return prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        species_label="Na",
        metadata={"source_identity_signature": source, "replica_id": "replica-A"},
    )


def _production_catalog(n_frames: int = 192, *, two_selected: bool = False):
    block_partition = QualityDiagnosticBlockPartition(
        source_identity_signature=SOURCE,
        trajectory_quality_verdict_signature="b" * 64,
        policy_signature="c" * 64,
        frame_count=n_frames,
        block_length_frames=16,
        block_boundaries=((0, n_frames),),
        block_center_times_ps=(0.5 * (n_frames - 1) * 0.001,),
        observable_autocorrelation_times_frames=(("temperature", 0.5),),
    )
    regime0 = ProductionRegime(
        regime_id="regime-0",
        frame_start=0,
        frame_stop=n_frames,
        time_start_ps=0.0,
        time_stop_ps=(n_frames - 1) * 0.001,
        block_start=0,
        block_stop=1,
        diagnostics=(),
        thermalization_status=ThermalizationEvidenceStatus.NO_DETECTED_TRANSIENT,
        stationarity_status=RegimeStationarityStatus.SUPPORTED,
        production_interval_status=ProductionIntervalStatus.SCIENTIFIC_CANDIDATE,
        selection_conditioning_status=SelectionConditioningStatus.FULL_SOURCE,
        quality_outcome=TrajectoryQualityOutcome.STRICTLY_QUALIFIED,
        scientific_use_permitted=True,
    )
    regimes = (regime0,)
    selected = ("regime-0",)
    if two_selected:
        regime1 = replace(regime0, regime_id="regime-1")
        regimes = (regime0, regime1)
        selected = ("regime-0", "regime-1")
    return ProductionRegimeCatalog(
        source_identity_signature=SOURCE,
        simulation_control_certificate_signature="d" * 64,
        trajectory_quality_verdict_signature="b" * 64,
        policy_signature="c" * 64,
        block_partition=block_partition,
        change_points=ChangePointCatalog(
            method="synthetic",
            status=ChangePointStatus.NONE,
            penalty=None,
            block_indices=(),
            frame_indices=(),
            segment_cost=None,
        ),
        regimes=regimes,
        selected_regime_ids=selected,
        overall_status=ProductionCatalogStatus.ACCEPTED,
    )


def _accepted_partition(*, nested: bool = False, final_refit: bool = False):
    policy = EvidenceCrossfitPolicy(
        mode=(
            CrossfitPartitionMode.NESTED_DISCOVERY_SELECTION
            if nested
            else CrossfitPartitionMode.EXPLICIT_HOLDOUT
        ),
        minimum_block_frames=8,
        explicit_block_length_frames=8,
        nested_selection_folds=3,
        include_final_refit=final_refit,
    )
    adequacy = SamplingAdequacyPolicy(
        minimum_blocks_per_domain=tuple(
            (domain.value, 1 if nested else 2)
            for domain in (
                CrossfitDomain.DISCOVERY,
                CrossfitDomain.MODEL_SELECTION,
                CrossfitDomain.BASIN_VALIDATION,
                CrossfitDomain.CORRIDOR_VALIDATION,
                CrossfitDomain.THERMODYNAMIC_ESTIMATION,
                CrossfitDomain.THERMODYNAMIC_VALIDATION,
            )
        ),
        minimum_effective_samples_per_domain=1.0,
    )
    return build_evidence_crossfit_partition(
        production_regime_catalog=_production_catalog(),
        sample_catalogs=(_sample_catalog(),),
        policy=policy,
        adequacy_policy=adequacy,
    )


def test_explicit_crossfit_is_accepted_and_primary_domains_are_disjoint():
    result = _accepted_partition()
    assert result.status is CrossfitPartitionStatus.ACCEPTED
    primary = [set(result.block_ids_for(domain)) for domain in (
        CrossfitDomain.DISCOVERY,
        CrossfitDomain.MODEL_SELECTION,
        CrossfitDomain.BASIN_VALIDATION,
        CrossfitDomain.CORRIDOR_VALIDATION,
        CrossfitDomain.THERMODYNAMIC_ESTIMATION,
        CrossfitDomain.THERMODYNAMIC_VALIDATION,
    )]
    assert all(primary[i].isdisjoint(primary[j]) for i in range(6) for j in range(i + 1, 6))
    assert set().union(*primary) == {block.block_id for block in result.blocks}


def test_complete_system_blocks_keep_every_ion_from_a_frame_together():
    catalog = _sample_catalog()
    result = build_evidence_crossfit_partition(
        production_regime_catalog=_production_catalog(),
        sample_catalogs=(catalog,),
        policy=EvidenceCrossfitPolicy(
            minimum_block_frames=8, explicit_block_length_frames=8
        ),
        adequacy_policy=SamplingAdequacyPolicy(
            minimum_blocks_per_domain=tuple((domain.value, 2) for domain in (
                CrossfitDomain.DISCOVERY,
                CrossfitDomain.MODEL_SELECTION,
                CrossfitDomain.BASIN_VALIDATION,
                CrossfitDomain.CORRIDOR_VALIDATION,
                CrossfitDomain.THERMODYNAMIC_ESTIMATION,
                CrossfitDomain.THERMODYNAMIC_VALIDATION,
            )),
            minimum_effective_samples_per_domain=1.0,
        ),
    )
    for block in result.blocks:
        assert block.sample_count == block.frame_count * 2
        assert block.selected_atom_count == 2
    mask = result.sample_mask_for(catalog, CrossfitDomain.DISCOVERY)
    for frame in range(192):
        frame_mask = mask[catalog.frame_indices == frame]
        assert frame_mask.size == 2
        assert bool(np.all(frame_mask)) or not bool(np.any(frame_mask))


def test_nested_selection_is_confined_to_shared_discovery_pool():
    result = _accepted_partition(nested=True)
    assert result.nested_selection_plan is not None
    discovery = set(result.block_ids_for(CrossfitDomain.DISCOVERY))
    assert discovery == set(result.block_ids_for(CrossfitDomain.MODEL_SELECTION))
    heldout = set().union(*(
        set(result.block_ids_for(domain))
        for domain in (
            CrossfitDomain.BASIN_VALIDATION,
            CrossfitDomain.CORRIDOR_VALIDATION,
            CrossfitDomain.THERMODYNAMIC_ESTIMATION,
            CrossfitDomain.THERMODYNAMIC_VALIDATION,
        )
    ))
    assert discovery.isdisjoint(heldout)
    for fold in result.nested_selection_plan.folds:
        assert set(fold.training_block_ids).issubset(discovery)
        assert set(fold.model_selection_block_ids).issubset(discovery)


def test_final_refit_is_all_blocks_with_a_distinct_domain_signature():
    result = _accepted_partition(final_refit=True)
    assert set(result.block_ids_for(CrossfitDomain.FINAL_REFIT)) == {
        block.block_id for block in result.blocks
    }
    assert result.domain_signature(CrossfitDomain.FINAL_REFIT) != result.domain_signature(
        CrossfitDomain.DISCOVERY
    )


def test_too_few_blocks_fails_closed_as_insufficient():
    result = build_evidence_crossfit_partition(
        production_regime_catalog=_production_catalog(24),
        sample_catalogs=(_sample_catalog(24),),
        policy=EvidenceCrossfitPolicy(
            minimum_block_frames=8, explicit_block_length_frames=8
        ),
    )
    assert result.status is CrossfitPartitionStatus.INSUFFICIENT
    assert any(item.reasons for item in result.domain_diagnostics)


def test_cross_source_catalog_is_rejected():
    with pytest.raises(SourceControlError, match="source identity mismatch"):
        build_evidence_crossfit_partition(
            production_regime_catalog=_production_catalog(),
            sample_catalogs=(_sample_catalog(source="f" * 64),),
        )


def test_multiple_selected_regimes_are_never_pooled_implicitly():
    with pytest.raises(SourceControlError, match="never pooled implicitly"):
        build_evidence_crossfit_partition(
            production_regime_catalog=_production_catalog(two_selected=True),
            sample_catalogs=(_sample_catalog(),),
        )


def test_partition_serialization_replays_exactly_and_detects_tampering():
    result = _accepted_partition(final_refit=True)
    rebuilt = EvidenceCrossfitPartition.from_dict(result.to_dict())
    assert rebuilt.signature == result.signature
    payload = result.to_dict()
    payload["resolved_block_length_frames"] += 1
    with pytest.raises(Exception, match="signature mismatch"):
        EvidenceCrossfitPartition.from_dict(payload)


def test_feature_correspondence_v1_has_exact_cost_and_type_contract():
    policy = FeatureCorrespondencePolicy()
    assert policy.policy_version == "stage11_feature_correspondence_v1"
    assert (policy.distance_weight, policy.overlap_weight, policy.probability_weight) == (1.0, 2.0, 1.0)
    assert policy.maximum_assignment_cost == 3.0
    assert policy.ambiguity_margin == 0.10
    assert policy.normalized_cost(
        distance=0.5,
        overlap=0.75,
        probability_left=0.30,
        probability_right=0.20,
        sigma_min=0.5,
        probability_scale=0.10,
        left_type=FeatureType.POINT,
        right_type=FeatureType.POINT,
    ) == pytest.approx(2.5)
    assert np.isinf(policy.normalized_cost(
        distance=0.0,
        overlap=1.0,
        probability_left=0.2,
        probability_right=0.2,
        sigma_min=1.0,
        probability_scale=1.0,
        left_type=FeatureType.POINT,
        right_type=FeatureType.RIDGE,
    ))


def test_samp0_public_exports_are_stable():
    assert mdstats.build_evidence_crossfit_partition is build_evidence_crossfit_partition
    assert "EvidenceCrossfitPartition" in mdstats.__all__
    assert "FeatureCorrespondencePolicy" in mdstats.__all__


def test_custom_replica_metadata_key_is_used_consistently():
    catalog = _sample_catalog()
    metadata = dict(catalog.metadata)
    metadata.pop("replica_id")
    metadata["trajectory_replica"] = "replica-custom"
    catalog = replace(catalog, metadata=metadata, signature="")
    policy = EvidenceCrossfitPolicy(
        minimum_block_frames=8,
        explicit_block_length_frames=8,
        replica_metadata_key="trajectory_replica",
    )
    adequacy = SamplingAdequacyPolicy(
        minimum_blocks_per_domain=tuple(
            (domain.value, 2)
            for domain in (
                CrossfitDomain.DISCOVERY,
                CrossfitDomain.MODEL_SELECTION,
                CrossfitDomain.BASIN_VALIDATION,
                CrossfitDomain.CORRIDOR_VALIDATION,
                CrossfitDomain.THERMODYNAMIC_ESTIMATION,
                CrossfitDomain.THERMODYNAMIC_VALIDATION,
            )
        ),
        minimum_effective_samples_per_domain=1.0,
    )
    result = build_evidence_crossfit_partition(
        production_regime_catalog=_production_catalog(),
        sample_catalogs=(catalog,),
        policy=policy,
        adequacy_policy=adequacy,
    )
    assert result.status is CrossfitPartitionStatus.ACCEPTED
    assert all(block.replica_ids == ("replica-custom",) for block in result.blocks)


def test_overlapping_mobile_atom_catalogs_are_rejected():
    first = _sample_catalog()
    second = replace(first, species_label="Na-overlap", signature="")
    with pytest.raises(SourceControlError, match="overlap mobile atom identities"):
        build_evidence_crossfit_partition(
            production_regime_catalog=_production_catalog(),
            sample_catalogs=(first, second),
        )


def test_nested_short_pool_returns_signed_insufficient_partition():
    result = build_evidence_crossfit_partition(
        production_regime_catalog=_production_catalog(24),
        sample_catalogs=(_sample_catalog(24),),
        policy=EvidenceCrossfitPolicy(
            mode=CrossfitPartitionMode.NESTED_DISCOVERY_SELECTION,
            minimum_block_frames=8,
            explicit_block_length_frames=8,
            nested_selection_folds=3,
        ),
    )
    assert result.status is CrossfitPartitionStatus.INSUFFICIENT
    assert result.nested_selection_plan is None
    assert EvidenceCrossfitPartition.from_dict(result.to_dict()).signature == result.signature


def test_data1_refactor_preserves_frozen_nested_partition_signature():
    result = _accepted_partition(nested=True, final_refit=True)
    assert result.signature == "ffe60aaef41492b7c76b1f98dfe155d989e8b3c4f7e90e1cc85af5680433509c"
