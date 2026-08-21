from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_cli
from tests.test_mlff_data5_partition_roles import _build


def _frames_for_units(bundle: mdstats.Data5PartitionBundle, unit_ids: tuple[str, ...]) -> set[str]:
    return {
        frame_uid
        for unit_id in unit_ids
        for frame_uid in bundle.unit_catalog.unit(unit_id).frame_uids
    }


def test_target_data2a_freezes_only_data5_development_authority(tmp_path: Path) -> None:
    sources, frames, _, bundle = _build(tmp_path)
    freeze = mdstats.build_target_data_role_freeze(sources, frames, bundle)

    outer = bundle.outer_partitions[0]
    domain = freeze.domain(outer.label_domain_id)
    expected_development = tuple(outer.units_for(mdstats.OuterRole.DEVELOPMENT))
    expected_final_validation = tuple(outer.units_for(mdstats.OuterRole.OUTER_MONITOR))

    assert set(domain.size_development_unit_ids) == set(expected_development)
    assert set(domain.size_development_frame_uids) == _frames_for_units(bundle, expected_development)
    assert set(domain.final_validation_unit_ids) == set(expected_final_validation)
    assert set(domain.final_validation_frame_uids) == _frames_for_units(bundle, expected_final_validation)
    assert {
        item.unit_id for item in domain.development_intervals
    } == set(expected_development)
    assert {
        uid for item in domain.development_intervals for uid in item.frame_uids
    } == set(domain.size_development_frame_uids)

    accepted = domain.size_development_frame_uids[:2]
    assert freeze.require_size_selection_frames(accepted) == accepted
    protected_uid = domain.final_validation_frame_uids[0]
    with pytest.raises(mdstats.TrainingDataInputError, match="outside the frozen training-eligible development domain"):
        freeze.require_size_selection_frames((protected_uid,))


def test_target_data2a_digest_and_round_trip_are_restart_stable(tmp_path: Path) -> None:
    sources, frames, _, bundle = _build(tmp_path)
    first = mdstats.build_target_data_role_freeze(sources, frames, bundle)
    second = mdstats.build_target_data_role_freeze(sources, frames, bundle)

    assert first.content_digest == second.content_digest
    restored = mdstats.TargetDataRoleFreeze.from_dict(first.to_dict())
    assert restored == first
    assert restored.content_digest == first.content_digest
    assert restored.policy.policy_digest == first.policy.policy_digest


def test_target_data2a_fails_closed_when_declared_family_crosses_cv_evidence_roles(tmp_path: Path) -> None:
    sources, frames, _, bundle = _build(tmp_path)
    fold = bundle.cross_validation_plans[0].folds[0]
    assert fold.training_unit_ids and fold.evaluation_unit_ids
    train_unit = bundle.unit_catalog.unit(fold.training_unit_ids[0])
    eval_unit = bundle.unit_catalog.unit(fold.evaluation_unit_ids[0])
    declared = {
        train_unit.frame_uids[0]: "authenticated-near-duplicate-family",
        eval_unit.frame_uids[0]: "authenticated-near-duplicate-family",
    }

    with pytest.raises(mdstats.TrainingDataInputError, match=r"declared_structural family .* crosses CV fold 0 evidence roles"):
        mdstats.build_target_data_role_freeze(
            sources,
            frames,
            bundle,
            declared_structural_family_by_frame_uid=declared,
        )


def test_target_data2a_rejects_declared_family_frame_outside_data5(tmp_path: Path) -> None:
    sources, frames, _, bundle = _build(tmp_path)
    unknown = "0" * 64
    with pytest.raises(mdstats.TrainingDataInputError, match="contains frames outside DATA5"):
        mdstats.build_target_data_role_freeze(
            sources,
            frames,
            bundle,
            declared_structural_family_by_frame_uid={unknown: "bad-family"},
        )


def test_target_data2a_campaign_migration_needs_no_data4_record(tmp_path: Path) -> None:
    sources, frames, _, bundle = _build(tmp_path / "inputs")
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite")
    store.put_record("source_catalog", sources)
    store.put_record("frame_catalog", frames)
    store.put_record("data5", bundle)
    assert not store.has_record("data4")
    assert not store.has_record("target_data_role_freeze")

    first = campaign_cli._ensure_target_data_role_freeze(store)
    assert store.has_record("target_data_role_freeze")
    restored = store.get_record("target_data_role_freeze", mdstats.TargetDataRoleFreeze)
    assert restored.content_digest == first.content_digest

    second = campaign_cli._ensure_target_data_role_freeze(store)
    assert second.content_digest == first.content_digest
    assert not store.has_record("data4")


def test_target_data2a_is_bound_into_prepare_restart_contract() -> None:
    assert "target_data_role_freeze" in campaign_cli._PREPARE_RECEIPT_RECORD_KEYS
    contract = campaign_cli._prepare_contract_signature()
    assert contract["target_data2a_role_freeze_version"] == mdstats.TARGET_DATA_ROLE_FREEZE_VERSION


def test_target_data2a_explicit_source_correlation_assertion_is_fail_closed(tmp_path: Path) -> None:
    sources, frames, _, bundle = _build(tmp_path)
    policy = mdstats.TargetDataRoleFreezePolicy(
        explicit_correlation_group_assertion_keys=("regime",),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match=r"explicit_source_correlation family .* crosses independent outer roles"):
        mdstats.build_target_data_role_freeze(
            sources,
            frames,
            bundle,
            policy=policy,
        )


def test_target_data2a_broad_lineage_ids_are_provenance_not_default_grouping() -> None:
    policy = mdstats.TargetDataRoleFreezePolicy()
    assert "lineage_id" in policy.lineage_metadata_assertion_keys
    assert "active_learning_lineage_id" in policy.lineage_metadata_assertion_keys
    assert "lineage_id" not in policy.explicit_correlation_group_assertion_keys
    assert "active_learning_lineage_id" not in policy.explicit_correlation_group_assertion_keys
