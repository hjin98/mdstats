from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._common import digest
from tests.test_mlff_data5_partition_roles import _build, _policy


def _profiled_data(tmp_path: Path):
    sources, frames, data4, _ = _build(tmp_path)
    profile = mdstats.build_single_phase_material_profile(
        profile_id="generic-ionic-solid",
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        chemistry_modifiers=(mdstats.ChemistryModifier.IONIC,),
    )
    contracts = mdstats.build_material_profile_contracts(profile)
    profiled_data4 = replace(data4, material_profile_contracts=contracts)
    data5 = mdstats.build_data5_partition_bundle(
        sources,
        frames,
        profiled_data4,
        partition_policy=_policy(),
    )
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    return sources, frames, frame_data, profiled_data4, data5


def test_profile_driven_data6_builds_universal_features_without_lta(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5 = _profiled_data(tmp_path)
    bundle = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=None,
    )
    assert bundle.policy.build_universal_structural_features
    assert not bundle.policy.build_lta_selection_features
    assert bundle.lta_selection_features is None
    assert len(bundle.universal_structural_features) == 1
    catalog = bundle.universal_structural_features[0]
    assert catalog.material_profile_contracts_digest == data4.material_profile_contracts.content_digest
    assert {item.symbol for item in catalog.atomic_environment_descriptors} == {"Li", "O"}
    assert all("ring" not in name.lower() and "lta" not in name.lower() for name in catalog.frame_descriptors[0].feature_names)
    assert mdstats.Data6FeatureBundle.from_dict(bundle.to_dict()) == bundle


def test_universal_catalog_is_generic_serializable_and_tamper_evident(tmp_path: Path) -> None:
    _, frames, frame_data, data4, data5 = _profiled_data(tmp_path)
    development = tuple(
        sorted(
            frame_uid
            for outer in data5.outer_partitions
            for unit_id in outer.units_for(mdstats.OuterRole.DEVELOPMENT)
            for frame_uid in data5.unit_catalog.unit(unit_id).frame_uids
        )
    )
    catalog = mdstats.build_universal_structural_feature_catalog(
        frames,
        frame_data,
        data4,
        frame_uids=development,
    )
    assert catalog.frame_descriptors
    assert catalog.atomic_environment_descriptors
    assert {item.atomic_number for item in catalog.atomic_environment_descriptors} == {3, 8}
    assert mdstats.UniversalStructuralFeatureCatalog.from_dict(catalog.to_dict()) == catalog
    tampered = deepcopy(catalog.to_dict())
    tampered["frame_descriptor_table"]["values"][0][0] += 1.0
    with pytest.raises(mdstats.TrainingDataSerializationError):
        mdstats.UniversalStructuralFeatureCatalog.from_dict(tampered)


def test_generic_structural_events_are_geometry_only(tmp_path: Path) -> None:
    _, frames, frame_data, data4, data5 = _profiled_data(tmp_path)
    selected = tuple(record.frame_uid for record in frames.frames[:5])
    policy = mdstats.UniversalStructuralSelectionPolicy(
        displacement_event_threshold_angstrom=1.0e-4,
        coordination_event_threshold=1.0e-8,
        density_event_threshold_angstrom3_inv=1.0e-8,
        orientational_event_threshold=1.0e-8,
    )
    catalog = mdstats.build_universal_structural_feature_catalog(
        frames,
        frame_data,
        data4,
        frame_uids=selected,
        policy=policy,
    )
    assert catalog.events
    assert {event.event_type for event in catalog.events} <= {
        "large_atomic_displacement",
        "smooth_coordination_change",
        "hard_neighbor_count_change",
        "local_density_change",
        "bond_orientational_q6_change",
    }
    assert all("ring" not in event.event_type for event in catalog.events)


def test_data6_v1_payload_remains_readable(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5 = _profiled_data(tmp_path)
    current = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=mdstats.Data6Policy(
            build_universal_structural_features=False,
            build_lta_selection_features=False,
        ),
    )
    payload = current.to_dict()
    legacy_policy = {
        "schema": "mdstats.data6-policy.v1",
        "policy_version": "mdstats.mlff-data6.bundle.2026-07.v1",
        "build_lta_selection_features": False,
        "build_mace_descriptors": False,
        "build_training_difficulty": False,
        "build_blinded_predictions": False,
        "descriptor_roles": list(current.policy.descriptor_roles),
    }
    legacy_policy["policy_digest"] = digest(legacy_policy)
    legacy = {
        key: value
        for key, value in payload.items()
        if key not in {"content_digest", "universal_structural_features"}
    }
    legacy["schema"] = "mdstats.data6-feature-bundle.v1"
    legacy["parser_version"] = "0.20.34a0"
    legacy["policy"] = legacy_policy
    legacy["content_digest"] = digest(legacy)
    restored = mdstats.Data6FeatureBundle.from_dict(legacy)
    assert restored.universal_structural_features == ()
    assert not restored.policy.build_universal_structural_features


def test_universal_structural_roles_reject_locked_test_materialization() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="sealed"):
        mdstats.Data6Policy(
            build_universal_structural_features=True,
            build_lta_selection_features=False,
            universal_structural_roles=(mdstats.OuterRole.LOCKED_INTERPOLATION_TEST.value,),
        )


def test_universal_structural_block_fits_and_drives_generic_environment_selection(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5 = _profiled_data(tmp_path)
    data6 = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=None,
    )
    domains = mdstats.build_feature_fit_domains(data5)
    final = next(item for item in domains if item.kind is mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT)
    metric = mdstats.fit_feature_metric(
        frames,
        frame_data,
        data4,
        data5,
        data6,
        final,
        policy=mdstats.FeatureMetricPolicyTemplate(
            blocks=(mdstats.FeatureBlockPolicy("universal_structural", required=True),)
        ),
    )
    assert {item.block_name for item in metric.block_metrics} == {"universal_structural"}
    assert all(item.vector for item in metric.frame_features)
    plan = mdstats.build_training_selection_plan(
        data4,
        data5,
        data6,
        metric,
        policy=mdstats.SelectionBudgetPolicy(target_sizes=(8, 16)),
    )
    assert any("species_environment" in entry.reason_codes for entry in plan.master_order)


def test_universal_structural_parallel_and_serial_are_identical(tmp_path: Path) -> None:
    _, frames, frame_data, data4, _ = _profiled_data(tmp_path)
    selected = tuple(record.frame_uid for record in frames.frames[:12])
    policy = mdstats.UniversalStructuralSelectionPolicy(
        materialize_atomic_environments=False,
    )
    serial_messages: list[str] = []
    parallel_messages: list[str] = []
    serial = mdstats.build_universal_structural_feature_catalog(
        frames,
        frame_data,
        data4,
        frame_uids=selected,
        policy=policy,
        max_workers=1,
        progress_callback=serial_messages.append,
    )
    parallel = mdstats.build_universal_structural_feature_catalog(
        frames,
        frame_data,
        data4,
        frame_uids=selected,
        policy=policy,
        max_workers=2,
        progress_callback=parallel_messages.append,
    )
    assert parallel == serial
    assert parallel.content_digest == serial.content_digest
    assert any("workers=2" in message for message in parallel_messages)
    assert any("frame/s" in message for message in parallel_messages)


def test_universal_structural_rejects_negative_worker_count(tmp_path: Path) -> None:
    _, frames, frame_data, data4, _ = _profiled_data(tmp_path)
    with pytest.raises(mdstats.TrainingDataInputError, match="max_workers"):
        mdstats.build_universal_structural_feature_catalog(
            frames,
            frame_data,
            data4,
            frame_uids=(frames.frames[0].frame_uid,),
            policy=mdstats.UniversalStructuralSelectionPolicy(
                materialize_atomic_environments=False,
            ),
            max_workers=-1,
        )
