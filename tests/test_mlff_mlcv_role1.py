from __future__ import annotations

import json
from pathlib import Path

import pytest

import mdstats


def _h(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def _data5_fixture() -> mdstats.Data5PartitionBundle:
    path = Path(__file__).parent / "fixtures" / "legacy_schema_0_20_76" / "data5.json"
    return mdstats.Data5PartitionBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _replay_artifact(
    token: str,
    geometries: tuple[str, ...],
    *,
    label_mode: mdstats.ReplayLabelMode,
    foundation: str | None = None,
) -> mdstats.ReplayFileArtifact:
    return mdstats.ReplayFileArtifact(
        path=f"/{token}.xyz",
        sha256=_h(f"file:{token}"),
        configuration_count=len(geometries),
        atomic_numbers=(3, 8),
        geometry_identities=geometries,
        label_identities=tuple(_h(f"label:{token}:{i}") for i in range(len(geometries))),
        energy_key="REF_energy",
        forces_key="REF_forces",
        stress_key="REF_stress",
        stress_present_count=len(geometries),
        label_mode=label_mode,
        foundation_checkpoint_digest=foundation,
    )


def _pseudo_replay_plan() -> tuple[mdstats.ReplayPreparationPlan, mdstats.ReplayFileArtifact]:
    foundation = _h("foundation")
    train_geometries = tuple(_h(f"train-geometry-{i}") for i in range(3))
    monitor_geometries = tuple(_h(f"monitor-geometry-{i}") for i in range(2))
    train = _replay_artifact(
        "train-pseudo",
        train_geometries,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        foundation=foundation,
    )
    monitor_pseudo = _replay_artifact(
        "monitor-pseudo",
        monitor_geometries,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        foundation=foundation,
    )
    true_monitor = _replay_artifact(
        "monitor-true",
        monitor_geometries,
        label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )
    plan = mdstats.ReplayPreparationPlan(
        mode=mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL,
        train_artifact=train,
        monitor_artifact=monitor_pseudo,
    )
    return plan, true_monitor


def test_mlcv_authority_rejects_outer_fold_for_checkpoint_selection() -> None:
    outer = mdstats.MlcvDataRole.TARGET_OUTER_CV_EVALUATION
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.require_mlcv_checkpoint_stopping_role(outer)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.require_mlcv_checkpoint_ranking_role(outer)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.require_mlcv_topk_selection_role(outer)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.adaptive_training_stop_requested("missing.jsonl", 0, target_data_role=outer)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.rank_lightweight_run_champion(None, None, None, None, target_data_role=outer)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.build_campaign_finalist_queue(None, {}, None, target_data_role=outer)
    assert mdstats.mlcv_role_allows(outer, mdstats.MlcvEvidenceOperation.OUTER_CV_EVALUATION)


def test_final_d_is_selection_evidence_but_locked_e_is_not() -> None:
    d_role = mdstats.MlcvDataRole.TARGET_FINAL_VALIDATION
    e_role = mdstats.MlcvDataRole.TARGET_LOCKED_TEST
    for operation in (
        mdstats.MlcvEvidenceOperation.CHECKPOINT_STOP,
        mdstats.MlcvEvidenceOperation.CHECKPOINT_RANK,
        mdstats.MlcvEvidenceOperation.CHECKPOINT_TOPK_SELECTION,
        mdstats.MlcvEvidenceOperation.FINAL_SEED_SELECTION,
    ):
        assert mdstats.mlcv_role_allows(d_role, operation)
        assert not mdstats.mlcv_role_allows(e_role, operation)
    assert not mdstats.mlcv_role_allows(
        e_role, mdstats.MlcvEvidenceOperation.PHYSICAL_VERIFICATION_FALLBACK
    )
    assert mdstats.mlcv_role_allows(e_role, mdstats.MlcvEvidenceOperation.LOCKED_TEST_EVALUATION)


def test_role_catalog_freezes_data5_nested_cv_roles_and_split_authority() -> None:
    data5 = _data5_fixture()
    plan, true_monitor = _pseudo_replay_plan()
    domain = data5.cross_validation_plans[0].label_domain_id
    catalog = mdstats.build_mlcv_role_catalog(
        data5,
        domain,
        replay_plan=plan,
        true_replay_validation_artifact=true_monitor,
    )
    development = set(catalog.final_gradient_training_unit_ids)
    assert catalog.split_authority == "data5_correlation_aware_partition_units"
    assert catalog.partition_unit_catalog_digest == data5.unit_catalog.content_digest
    assert catalog.partition_policy_digest == data5.partition_policy.policy_digest
    assert len(catalog.folds) == 3
    held_out: set[str] = set()
    for fold, original in zip(catalog.folds, data5.cross_validation_plans[0].folds, strict=True):
        assert fold.gradient_training_unit_ids == original.training_unit_ids
        assert fold.checkpoint_selection_unit_ids == original.checkpoint_monitor_unit_ids
        assert fold.outer_evaluation_unit_ids == original.evaluation_unit_ids
        groups = (
            set(fold.gradient_training_unit_ids),
            set(fold.checkpoint_selection_unit_ids),
            set(fold.outer_evaluation_unit_ids),
            set(fold.purged_unit_ids),
        )
        assert set().union(*groups) == development
        assert all(not groups[i] & groups[j] for i in range(4) for j in range(i + 1, 4))
        held_out.update(fold.outer_evaluation_unit_ids)
    assert held_out == development
    assert not development & set(catalog.final_validation_unit_ids)
    assert not development & set(catalog.locked_test_unit_ids)
    assert not set(catalog.final_validation_unit_ids) & set(catalog.locked_test_unit_ids)
    assert mdstats.MlcvRoleCatalog.from_dict(catalog.to_dict()) == catalog


def test_replay_training_and_true_validation_lineage_are_typed_and_disjoint() -> None:
    plan, true_monitor = _pseudo_replay_plan()
    lineage = mdstats.build_mlcv_replay_role_lineage(plan, true_monitor)
    assert lineage.training_label_mode is mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert lineage.validation_label_mode is mdstats.ReplayLabelMode.TRUE_DFT
    assert lineage.training_artifact_digest != lineage.validation_artifact_digest
    assert lineage.training_validation_geometry_overlap_count == 0
    assert mdstats.MlcvReplayRoleLineage.from_dict(lineage.to_dict()) == lineage

    pseudo_as_validation = plan.monitor_artifact
    assert pseudo_as_validation is not None
    with pytest.raises(mdstats.TrainingDataInputError, match="TRUE_DFT"):
        mdstats.build_mlcv_replay_role_lineage(plan, pseudo_as_validation)

    train = plan.train_artifact
    assert train is not None
    true_overlap = _replay_artifact(
        "true-overlap",
        train.geometry_identities,
        label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="disjoint"):
        mdstats.build_mlcv_replay_role_lineage(plan, true_overlap)



def test_role_catalog_uses_variant_cross_validation_plan_when_supplied() -> None:
    data5 = _data5_fixture()
    plan, true_monitor = _pseudo_replay_plan()
    variant = mdstats.build_cross_validation_plans(
        data5.unit_catalog,
        data5.outer_partitions,
        data5.feasibility_reports,
        policy=data5.partition_policy,
        fold_count_override=3,
        fold_seed_override=99991,
    )[0]
    catalog = mdstats.build_mlcv_role_catalog(
        data5,
        variant.label_domain_id,
        replay_plan=plan,
        true_replay_validation_artifact=true_monitor,
        cross_validation_plan=variant,
    )
    assert catalog.cross_validation_plan_digest == variant.content_digest
    assert tuple(f.outer_evaluation_unit_ids for f in catalog.folds) == tuple(
        f.evaluation_unit_ids for f in variant.folds
    )

def test_locked_test_remains_sealed_in_data8_contract() -> None:
    artifact = mdstats.SealedEvaluationArtifact(
        role="locked_interpolation_test",
        label_domain_id="domain",
        frame_uids=(_h("frame"),),
        frame_catalog_digest=_h("frames"),
        data5_bundle_digest=_h("data5"),
    )
    assert artifact.materialized is False
    assert artifact.activation_requirement == "ProtocolFreezeRecord"
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.SealedEvaluationArtifact(
            role="locked_interpolation_test",
            label_domain_id="domain",
            frame_uids=(_h("frame"),),
            frame_catalog_digest=_h("frames"),
            data5_bundle_digest=_h("data5"),
            materialized=True,
        )
