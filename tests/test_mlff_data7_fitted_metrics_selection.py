from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

import mdstats
from tests.test_mlff_data5_partition_roles import _build
from tests.test_mlff_data6_selection_descriptors import _provider


def _inputs(tmp_path: Path, *, model: bool = False):
    sources, frames, data4, data5 = _build(tmp_path)
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    if model:
        provider = _provider()
        data6 = mdstats.build_data6_feature_bundle(
            sources,
            frames,
            frame_data,
            data4,
            data5,
            policy=mdstats.Data6Policy(
                build_lta_selection_features=False,
                build_mace_descriptors=True,
                build_training_difficulty=True,
                build_blinded_predictions=False,
            ),
            model_provider=provider,
            descriptor_output_directory=tmp_path / "descriptors",
        )
    else:
        data6 = mdstats.build_data6_feature_bundle(
            sources,
            frames,
            frame_data,
            data4,
            data5,
            policy=mdstats.Data6Policy(
                build_lta_selection_features=False,
                build_mace_descriptors=False,
                build_training_difficulty=False,
                build_blinded_predictions=False,
            ),
        )
    domains = mdstats.build_feature_fit_domains(data5)
    final = next(item for item in domains if item.kind is mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT)
    return sources, frames, frame_data, data4, data5, data6, domains, final


def test_supplied_ase_version() -> None:
    import ase

    assert ase.__version__ == "3.29.0"


def test_fold_local_feature_metrics_do_not_include_monitors_or_evaluation(tmp_path: Path) -> None:
    _, frames, frame_data, data4, data5, data6, domains, _ = _inputs(tmp_path)
    fold = next(item for item in domains if item.kind is mdstats.FeatureFitDomainKind.CROSS_VALIDATION_TRAINING)
    policy = mdstats.FeatureMetricPolicyTemplate(
        blocks=(mdstats.FeatureBlockPolicy("raw_physical", required=True),)
    )
    metric = mdstats.fit_feature_metric(frames, frame_data, data4, data5, data6, fold, policy=policy)
    assert {item.frame_uid for item in metric.frame_features} == set(fold.frame_uids)
    plan = next(item for item in data5.cross_validation_plans if item.label_domain_id == fold.label_domain_id)
    source_fold = plan.folds[fold.fold_index]
    forbidden_units = source_fold.checkpoint_monitor_unit_ids + source_fold.evaluation_unit_ids + source_fold.purged_unit_ids
    forbidden = {
        uid for unit_id in forbidden_units for uid in data5.unit_catalog.unit(unit_id).frame_uids
    }
    assert not forbidden & set(fold.frame_uids)
    assert mdstats.FittedFeatureMetric.from_dict(metric.to_dict()) == metric


def test_metric_block_dimension_normalization_and_model_sidecars(tmp_path: Path) -> None:
    _, frames, frame_data, data4, data5, data6, _, final = _inputs(tmp_path, model=True)
    policy = mdstats.FeatureMetricPolicyTemplate(
        blocks=(
            mdstats.FeatureBlockPolicy("raw_physical", weight=1.0, required=True),
            mdstats.FeatureBlockPolicy("mace_summary", weight=2.0, pca_components=4, required=True),
            mdstats.FeatureBlockPolicy("difficulty", weight=0.5, required=True),
        )
    )
    metric = mdstats.fit_feature_metric(
        frames,
        frame_data,
        data4,
        data5,
        data6,
        final,
        policy=policy,
        mace_descriptor_root=tmp_path / "descriptors",
    )
    by_name = {item.block_name: item for item in metric.block_metrics}
    assert by_name["mace_summary"].output_dimension == 4
    assert by_name["mace_summary"].weight_factor == pytest.approx(np.sqrt(2.0 / 4.0))
    assert by_name["difficulty"].weight_factor == pytest.approx(
        np.sqrt(0.5 / by_name["difficulty"].output_dimension)
    )
    assert all(np.isfinite(np.asarray(item.vector)).all() for item in metric.frame_features)


def test_atomic_reference_fits_are_domain_local_and_rank_audited(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, _, domains, final = _inputs(tmp_path)
    final_fit = mdstats.fit_atomic_reference_energies(frames, frame_data, data5, final)
    assert tuple(final_fit.explicit_mapping) == final_fit.element_order
    assert len(final_fit.count_matrix) == len(final.frame_uids)
    assert final_fit.rank_deficient
    assert final_fit.transfer_warnings
    fold = next(item for item in domains if item.kind is mdstats.FeatureFitDomainKind.CROSS_VALIDATION_TRAINING)
    fold_fit = mdstats.fit_atomic_reference_energies(frames, frame_data, data5, fold)
    assert len(fold_fit.count_matrix) == len(fold.frame_uids)
    assert fold_fit.domain.content_digest != final_fit.domain.content_digest
    assert mdstats.AtomicReferenceFitRecord.from_dict(final_fit.to_dict()) == final_fit
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.fit_atomic_reference_energies(
            frames,
            frame_data,
            data5,
            final,
            policy=mdstats.AtomicReferenceFitPolicy(allow_rank_deficient_fixed_domain=False),
        )


def test_training_weights_separate_configuration_and_property_weights(tmp_path: Path) -> None:
    _, frames, _, data4, data5, _, _, final = _inputs(tmp_path)
    catalog = mdstats.build_training_weight_catalog(
        frames,
        data4,
        data5,
        final,
        objective_policy=mdstats.TrainingObjectivePolicy(energy_weight=1.0, forces_weight=10.0, stress_weight=0.5),
        configuration_policy=mdstats.ConfigurationWeightPolicy(event_anchor_multiplier=3.0),
    )
    assert np.mean([item.configuration_weight for item in catalog.records]) == pytest.approx(1.0)
    assert {item.energy_weight for item in catalog.records} == {1.0}
    assert {item.forces_weight for item in catalog.records} == {10.0}
    assert {item.stress_weight for item in catalog.records} == {0.5}
    anchors = {event.anchor_frame_uid for event in data4.events.events} & set(final.frame_uids)
    if anchors:
        assert max(catalog.for_frame(uid).configuration_weight for uid in anchors) > min(
            item.configuration_weight for item in catalog.records
        )
    assert mdstats.TrainingWeightCatalog.from_dict(catalog.to_dict()) == catalog


def test_quota_interleaved_master_order_is_deterministic_and_nested(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5, data6, _, final = _inputs(tmp_path, model=True)
    metric_policy = mdstats.FeatureMetricPolicyTemplate(
        blocks=(
            mdstats.FeatureBlockPolicy("raw_physical", required=True),
            mdstats.FeatureBlockPolicy("mace_summary", weight=1.0, pca_components=3, required=True),
            mdstats.FeatureBlockPolicy("difficulty", weight=0.5, required=True),
        )
    )
    metric = mdstats.fit_feature_metric(
        frames,
        frame_data,
        data4,
        data5,
        data6,
        final,
        policy=metric_policy,
        mace_descriptor_root=tmp_path / "descriptors",
    )
    policy = mdstats.SelectionBudgetPolicy(target_sizes=(8, 16, 24))
    first = mdstats.build_training_selection_plan(data4, data5, data6, metric, policy=policy)
    second = mdstats.build_training_selection_plan(data4, data5, data6, metric, policy=policy)
    assert first == second
    assert len(first.master_order) == 24
    assert first.ladder_levels[0].frame_uids == first.ladder_levels[1].frame_uids[:8]
    assert first.ladder_levels[1].frame_uids == first.ladder_levels[2].frame_uids[:16]
    assert any("difficulty" in entry.reason_codes for entry in first.master_order[:24])
    assert any("rare_event" in entry.reason_codes for entry in first.master_order[:24])
    coverage = mdstats.build_selection_coverage_report(data4, data5, data6, metric, first)
    assert coverage.levels[-1].maximum_covering_radius <= coverage.levels[0].maximum_covering_radius
    assert mdstats.TrainingSelectionPlan.from_dict(first.to_dict()) == first
    assert mdstats.SelectionCoverageReport.from_dict(coverage.to_dict()) == coverage

    bundle = mdstats.build_data7_preparation_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        data6,
        final,
        feature_metric_policy=metric_policy,
        selection_budget_policy=policy,
        mace_descriptor_root=tmp_path / "descriptors",
    )
    assert mdstats.Data7PreparationBundle.from_dict(bundle.to_dict()) == bundle
    tampered = deepcopy(bundle.to_dict())
    tampered["notes"] = ["modified"]
    with pytest.raises(mdstats.TrainingDataSerializationError):
        mdstats.Data7PreparationBundle.from_dict(tampered)


def test_noncanonical_domain_and_infeasible_ladder_fail_closed(tmp_path: Path) -> None:
    _, frames, frame_data, data4, data5, data6, _, final = _inputs(tmp_path)
    ad_hoc = mdstats.FeatureFitDomain(
        label_domain_id=final.label_domain_id,
        kind=final.kind,
        data5_bundle_digest=final.data5_bundle_digest,
        unit_ids=final.unit_ids,
        frame_uids=final.frame_uids[:-1],
    )
    policy = mdstats.FeatureMetricPolicyTemplate(
        blocks=(mdstats.FeatureBlockPolicy("raw_physical", required=True),)
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.fit_feature_metric(frames, frame_data, data4, data5, data6, ad_hoc, policy=policy)
    metric = mdstats.fit_feature_metric(frames, frame_data, data4, data5, data6, final, policy=policy)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.build_training_selection_plan(
            data4,
            data5,
            data6,
            metric,
            policy=mdstats.SelectionBudgetPolicy(target_sizes=(len(final.frame_uids) + 1,)),
        )


def test_implicit_missing_indicator_pca_matches_explicit_randomized_projection() -> None:
    from mdstats.training_data.feature_metric import (
        _implicit_missing_indicator_projection,
        _orient_projection_rows,
        _principal_projection,
    )

    rng = np.random.default_rng(20260805)
    standardized = rng.normal(size=(1001, 1000))
    missing = rng.random((1001, 1000)) < 0.075
    implicit_projection, implicit_output = _implicit_missing_indicator_projection(
        standardized,
        missing,
        12,
        row_chunk=173,
    )
    explicit = np.concatenate(
        (standardized, missing.astype(np.float64)), axis=1
    )
    explicit_projection = _principal_projection(explicit, 12)
    _orient_projection_rows(explicit_projection)
    explicit_output = explicit @ explicit_projection.T
    assert np.allclose(
        implicit_projection,
        explicit_projection,
        rtol=2e-10,
        atol=2e-10,
    )
    assert np.allclose(
        implicit_output,
        explicit_output,
        rtol=2e-10,
        atol=5e-10,
    )
