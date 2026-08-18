from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats
from mdstats.training_data._common import digest
from tests.test_mlff_data4_raw_features_events import _site_catalogs
from tests.test_mlff_data5_partition_roles import _policy


def _lta_contracts() -> mdstats.MaterialProfileContracts:
    profile = mdstats.build_single_phase_material_profile(
        profile_id="lta-extension-profile",
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        chemistry_modifiers=(mdstats.ChemistryModifier.IONIC,),
        extensions=(
            mdstats.StructuralExtension.POROUS_NETWORK,
            mdstats.StructuralExtension.ZEOLITE,
            mdstats.StructuralExtension.LTA,
        ),
    )
    return mdstats.build_material_profile_contracts(profile)


def _lta_data4(tmp_path):
    sources, frames, frame_data, site_policy = _site_catalogs(tmp_path)
    data4 = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        frame_data,
        material_profile_contracts=_lta_contracts(),
        lta_profile_policy=mdstats.LtaPartitionProfilePolicy(
            ring_definitions=site_policy.ring_definitions,
            require_oxygen_framework_coordination=1,
        ),
        partition_role_budget=mdstats.PartitionRoleBudgetPolicy(cross_validation_folds=2),
    )
    return sources, frames, frame_data, data4


def test_lta_is_canonicalized_as_optional_profile_extension(tmp_path) -> None:
    _, _, _, data4 = _lta_data4(tmp_path)
    assert tuple(item.extension_id for item in data4.profile_partition_features) == ("lta",)
    assert mdstats.find_profile_feature(data4.profile_partition_features, "lta") is not None
    payload = data4.to_dict()
    assert "profile_partition_features" in payload
    assert "lta_partition_features" not in payload
    assert mdstats.Data4FeatureBundle.from_dict(payload) == data4


def test_lta_selection_extension_round_trip_and_common_adapters(tmp_path) -> None:
    _, frames, frame_data, data4 = _lta_data4(tmp_path)
    lta = mdstats.build_lta_selection_feature_catalog(frames, frame_data, data4)
    wrapped = mdstats.wrap_lta_selection_features(
        lta, data4_bundle_digest=data4.content_digest
    )
    restored = mdstats.ProfileFeatureCatalog.from_dict(wrapped.to_dict())
    assert restored.as_lta_selection() == lta
    uid = lta.frame_descriptors[0].frame_uid
    names, values, missing = restored.frame_feature_vector(uid)
    assert names and len(names) == len(values) == len(missing)
    assert all(name.startswith("lta:") for name in names)
    assert restored.atomic_environment_descriptors()
    assert restored.environment_class_labels((uid,))



def test_data6_canonicalizes_lta_selection_as_profile_extension(tmp_path) -> None:
    sources, frames, frame_data, data4 = _lta_data4(tmp_path)
    lta = mdstats.build_lta_selection_feature_catalog(frames, frame_data, data4)
    wrapped = mdstats.wrap_lta_selection_features(lta, data4_bundle_digest=data4.content_digest)
    data6 = mdstats.Data6FeatureBundle(
        dataset_id=frames.dataset_id,
        source_catalog_digest=sources.content_digest,
        frame_catalog_digest=frames.content_digest,
        data4_bundle_digest=data4.content_digest,
        data5_bundle_digest="f" * 64,
        policy=mdstats.Data6Policy(),
        lta_selection_features=None,
        checkpoint_identity=None,
        mace_descriptor_manifest=None,
        training_difficulty_catalogs=(),
        blinded_prediction_catalogs=(),
        profile_selection_features=(wrapped,),
    )
    assert tuple(item.extension_id for item in data6.profile_selection_features) == ("lta",)
    assert mdstats.find_profile_feature(data6.profile_selection_features, "lta") is not None
    payload = data6.to_dict()
    assert "profile_selection_features" in payload
    assert "lta_selection_features" not in payload
    assert mdstats.Data6FeatureBundle.from_dict(payload) == data6

def test_generic_profile_cannot_consume_lta_extension(tmp_path) -> None:
    _, frames, frame_data, data4 = _lta_data4(tmp_path / "lta")
    lta = mdstats.build_lta_selection_feature_catalog(frames, frame_data, data4)
    wrapped = mdstats.wrap_lta_selection_features(lta, data4_bundle_digest=data4.content_digest)
    generic = mdstats.build_material_profile_contracts(
        mdstats.build_single_phase_material_profile(
            profile_id="generic", phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID
        )
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="explicit lta extension"):
        mdstats.normalize_profile_feature_catalogs(
            (wrapped,), stage=mdstats.ProfileFeatureStage.SELECTION, contracts=generic
        )


def test_focus_groups_replace_cation_defaults() -> None:
    profile = mdstats.build_single_phase_material_profile(
        profile_id="salt", phase_kind=mdstats.MaterialPhaseKind.LIQUID
    )
    all_atoms = mdstats.AtomGroupDefinition(
        group_id="all_atoms",
        label="All atoms",
        selector=mdstats.AtomGroupSelector(kind=mdstats.AtomGroupSelectorKind.ALL_ATOMS),
        phase_ids=("material",),
    )
    halides = mdstats.AtomGroupDefinition(
        group_id="halides",
        label="Halides",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS, atomic_numbers=(17,)
        ),
        phase_ids=("material",),
        roles=("mlff_focus",),
    )
    groups = mdstats.AtomGroupCatalog(
        material_profile_digest=profile.content_digest,
        material_phase_ids=profile.phase_ids,
        groups=(all_atoms, halides),
    )
    contracts = mdstats.build_material_profile_contracts(profile, atom_groups=groups)
    assert mdstats.focus_atom_group_ids(contracts) == ("halides",)
    assert mdstats.focus_atomic_numbers(contracts, atomic_numbers=(3, 17)) == (17,)
    objective = mdstats.TrainingObjectivePolicy(
        group_aware_force_objective=True,
        focus_atom_group_ids=("halides",),
    )
    checkpoint = mdstats.CheckpointMetricPolicy(
        focus_atom_group_ids=("halides",),
        maximum_focus_force_rmse_ev_per_angstrom=0.2,
    )
    assert not hasattr(objective, "cation_atomic_numbers")
    assert checkpoint.maximum_focus_force_rmse_ev_per_angstrom == pytest.approx(0.2)


def test_production_qualification_exposes_generic_extension_coverage() -> None:
    record = mdstats.ProductionCorpusQualificationRecord(
        production_plan_digest="f"*64,
        dataset_id="x", expected_source_count=1, source_count=1, total_frame_count=1,
        normalization_manifest_digest="a"*64, reference_manifest_digest="b"*64,
        run_evidence_digest="c"*64, source_catalog_digest="d"*64,
        frame_catalog_digest="e"*64, data4_bundle_digest=None, data5_bundle_digest=None,
        data6_bundle_digest=None, data7_bundle_digests=(), data8_bundle_digest=None,
        eligible_frame_count=1, degraded_frame_count=0, rejected_frame_count=0,
        unresolved_strain_frame_count=0, duplicate_geometry_group_count=0,
        duplicate_labeled_group_count=0, composition_formulas=("X",),
        target_temperatures_kelvin=(300.0,), ensembles=("nvt",),
        strain_class_counts=(), feasibility_outcomes=(), independence_grade_counts=(),
        event_type_counts=(), partition_unit_count=0, condition_count=0,
        cross_validation_fold_count=0, leakage_audit_passed=False,
        profile_extension_coverage_materialized=True, foundation_features_materialized=False,
        foundation_residual_e0_materialized=False, data8_artifacts_materialized=False,
        replay_corpus_bound=False, target_corpus_qualified=False, full_data9a_passed=False,
        status=mdstats.ProductionGateStatus.BLOCKED, blockers=("x",), warnings=(),
    )
    assert record.profile_extension_coverage_materialized is True
    payload = record.to_dict()
    assert payload["profile_extension_coverage_materialized"] is True
    assert "site_coverage_materialized" not in payload
    assert mdstats.ProductionCorpusQualificationRecord.from_dict(payload) == record
