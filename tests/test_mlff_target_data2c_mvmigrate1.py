from __future__ import annotations

from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data._common import digest
from tests.test_mlff_target_data2c_ladder import _reference_and_role


SIZES = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)


def _migration_upstream(*, qualified=SIZES[:4], nonregression=True):
    dataset_id = "synthetic"
    legacy = SimpleNamespace(dataset_id=dataset_id, content_digest=digest({"legacy": 4}))
    repair = SimpleNamespace(dataset_id=dataset_id, content_digest=digest({"repair": 1}))
    qualification = SimpleNamespace(
        dataset_id=dataset_id,
        content_digest=digest({"mvqual": 1, "qualified": tuple(qualified), "nonregression": nonregression}),
        legacy_target_data_ladder_digest=legacy.content_digest,
        target_multi_view_repair_digest=repair.content_digest,
        mv_qualified_sizes=tuple(qualified),
        same_n_non_regression_passed=bool(nonregression),
        n95_non_regression_passed=bool(nonregression),
        learning_control_target_sizes=(SIZES[2], SIZES[3]),
    )
    halve = SimpleNamespace(
        dataset_id=dataset_id,
        content_digest=digest({"halve": tuple(qualified)}),
        target_multi_view_repair_digest=repair.content_digest,
        target_multi_view_qualification_digest=qualification.content_digest,
        outcome="ready_for_size_fidelity2" if len(qualified) >= 4 and nonregression else "blocked_insufficient_hard_coverage",
    )
    fidelity = SimpleNamespace(
        dataset_id=dataset_id,
        content_digest=digest({"fidelity-plan": 1}),
        size_halve2_plan_digest=halve.content_digest,
        status="ready_for_final_gpu_calibration" if halve.outcome == "ready_for_size_fidelity2" else "blocked_by_size_halve2",
    )
    return legacy, repair, qualification, halve, fidelity


def _learning_report(qualification, *, mv_delta=0.5):
    rows = tuple(
        mdstats.TargetMultiViewLearningControlRow(
            target_size=size,
            optimizer_seed=1,
            legacy_target_force_score_mev_per_a=10.0,
            mv_target_force_score_mev_per_a=10.0 + mv_delta,
            practical_equivalence_mev_per_a=1.0,
            common_training_protocol_digest=digest({"train2": 1}),
            legacy_evaluation_digest=digest({"legacy-eval": size}),
            mv_evaluation_digest=digest({"mv-eval": size}),
        )
        for size in qualification.learning_control_target_sizes
    )
    return mdstats.TargetMultiViewLearningControlReport(
        dataset_id=qualification.dataset_id,
        target_multi_view_qualification_digest=qualification.content_digest,
        control_target_sizes=qualification.learning_control_target_sizes,
        rows=rows,
        gpu_qualification_status="passed",
    )


def _fidelity_report(fidelity, *, passed=True, gpu="passed"):
    return SimpleNamespace(
        dataset_id=fidelity.dataset_id,
        execution_plan_digest=fidelity.content_digest,
        content_digest=digest({"fidelity-report": passed, "gpu": gpu}),
        passed=bool(passed),
        gpu_qualification_status=gpu,
    )


def test_mvmigrate1_freezes_pending_latch_without_final_gpu_evidence():
    legacy, repair, qual, halve, fidelity = _migration_upstream()
    plan = mdstats.build_target_multi_view_migration_plan(
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qual,
        size_halve2_plan=halve,
        size_fidelity2_execution_plan=fidelity,
    )
    assert plan.status == "awaiting_final_gpu_qualification"
    assert not plan.activation_authorized
    assert plan.policy.target_sizes == SIZES
    assert plan.policy.minimum_hard_qualifiers == 4
    assert plan.policy.retire_dynamic_rescue is True
    assert plan.learning_control_report_digest is None
    assert plan.size_fidelity2_qualification_digest is None
    restored = mdstats.TargetMultiViewMigrationPlan.from_dict(plan.to_dict())
    assert restored.content_digest == plan.content_digest


def test_mvmigrate1_authorizes_only_when_both_final_gpu_authorities_pass():
    legacy, repair, qual, halve, fidelity = _migration_upstream()
    learning = _learning_report(qual)
    fidelity_report = _fidelity_report(fidelity)
    plan = mdstats.build_target_multi_view_migration_plan(
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qual,
        size_halve2_plan=halve,
        size_fidelity2_execution_plan=fidelity,
        learning_control_report=learning,
        size_fidelity2_qualification=fidelity_report,
    )
    assert plan.status == "authorized_for_atomic_activation"
    assert plan.activation_authorized
    mdstats.validate_target_multi_view_migration_plan(
        plan,
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qual,
        size_halve2_plan=halve,
        size_fidelity2_execution_plan=fidelity,
        learning_control_report=learning,
        size_fidelity2_qualification=fidelity_report,
    )


def test_mvmigrate1_blocks_scientific_or_gpu_regression():
    legacy, repair, qual, halve, fidelity = _migration_upstream(qualified=SIZES[:3])
    plan = mdstats.build_target_multi_view_migration_plan(
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qual,
        size_halve2_plan=halve,
        size_fidelity2_execution_plan=fidelity,
    )
    assert plan.status == "blocked_scientific_preconditions"
    assert "only 3 MV sizes" in plan.decision_reason

    legacy, repair, qual, halve, fidelity = _migration_upstream()
    bad_learning = _learning_report(qual, mv_delta=2.0)
    plan = mdstats.build_target_multi_view_migration_plan(
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qual,
        size_halve2_plan=halve,
        size_fidelity2_execution_plan=fidelity,
        learning_control_report=bad_learning,
        size_fidelity2_qualification=_fidelity_report(fidelity),
    )
    assert plan.status == "blocked_scientific_preconditions"
    assert "learning controls failed" in plan.decision_reason


def test_migrated_v5_ladder_is_fixed_eight_repair_prefix_no_rescue_and_v3_requires_four_qualifiers():
    reference, role = _reference_and_role(1024)
    ref_domain = reference.domain("target")

    class Repair:
        dataset_id = reference.dataset_id
        target_coverage_reference_digest = reference.content_digest
        content_digest = digest({"repair": "mvmigrate-fixture"})

        def __init__(self):
            self._domain = SimpleNamespace(
                label_domain_id="target",
                reference_domain_digest=ref_domain.content_digest,
                content_digest=digest({"repair-domain": "target"}),
                repaired_master_order=tuple(ref_domain.frame_uids),
                rungs=(),
            )
            self.domains = (self._domain,)

        def domain(self, label_domain_id):
            assert label_domain_id == "target"
            return self._domain

    repair = Repair()
    qualification_domain = SimpleNamespace(
        label_domain_id="target", mv_repair_domain_digest=repair.domain("target").content_digest
    )
    qualification = SimpleNamespace(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        target_data_role_freeze_digest=role.content_digest,
        target_multi_view_repair_digest=repair.content_digest,
        content_digest=digest({"mvqual": "mvmigrate-fixture"}),
        domains=(qualification_domain,),
    )
    migration_digest = digest({"migration": "pending-final-gpu"})
    ladder = mdstats.build_migrated_target_data_ladder(
        reference,
        role,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qualification,
        migration_authority_digest=migration_digest,
    )
    assert ladder.authority_version == mdstats.TARGET_DATA_LADDER_MV_VERSION
    assert ladder.policy.policy_version == mdstats.TARGET_DATA_LADDER_MV_POLICY_VERSION
    assert ladder.configured_candidate_sizes == SIZES
    assert ladder.materialized_target_sizes == SIZES[:4]
    assert ladder.coverage_rescue_activated is False
    assert ladder.coverage_rescue_candidate_sizes == ()
    assert ladder.coverage_rescue_min_qualifiers == 4
    assert ladder.target_multi_view_repair_digest == repair.content_digest
    assert ladder.target_multi_view_qualification_digest == qualification.content_digest
    assert ladder.migration_authority_digest == migration_digest
    assert tuple(item.frame_uid for item in ladder.domains[0].master_order) == tuple(ref_domain.frame_uids[:1024])
    mdstats.validate_migrated_target_data_ladder_authority(
        ladder,
        reference=reference,
        target_data_role_freeze=role,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qualification,
        migration_authority_digest=migration_digest,
    )
    restored = mdstats.TargetDataLadderPlan.from_dict(ladder.to_dict())
    assert restored.content_digest == ladder.content_digest
    with pytest.raises(mdstats.TargetDataCoverageError, match="fewer than 4 qualified rungs"):
        mdstats.build_target_size_convergence_plan(ladder)


def test_generation_specific_d2e_schema_constants_cannot_alias_historical_versions():
    assert mdstats.TARGET_DATA_LADDER_MV_VERSION != mdstats.TARGET_DATA_LADDER_VERSION
    assert mdstats.TARGET_SIZE_CONVERGENCE_MV_VERSION != mdstats.TARGET_SIZE_CONVERGENCE_VERSION
    assert mdstats.TARGET_PRODUCTION_CORPUS_MV_VERSION != mdstats.TARGET_PRODUCTION_CORPUS_VERSION
    policy = mdstats.TargetSizeConvergencePolicy(
        min_coverage_qualifiers=4,
        policy_version=mdstats.TARGET_SIZE_CONVERGENCE_MV_VERSION,
    )
    payload = policy.to_dict()
    assert payload["schema"] == mdstats.TARGET_SIZE_CONVERGENCE_MV_POLICY_SCHEMA
    masquerade = dict(payload)
    masquerade["schema"] = mdstats.TARGET_SIZE_CONVERGENCE_POLICY_SCHEMA
    with pytest.raises(mdstats.TrainingDataSerializationError, match="schema/version generation mismatch"):
        mdstats.TargetSizeConvergencePolicy.from_dict(masquerade)
    with pytest.raises(mdstats.TrainingDataInputError, match="freezes min_coverage_qualifiers at four"):
        mdstats.TargetSizeConvergencePolicy(
            min_coverage_qualifiers=3,
            policy_version=mdstats.TARGET_SIZE_CONVERGENCE_MV_VERSION,
        )


def test_mvmigrate1_activation_receipt_roundtrip_and_fail_closed_status():
    values = {name: digest({name: 1}) for name in (
        "final", "learning", "fidelity", "migration", "legacy", "ladder", "convergence", "production"
    )}
    receipt = mdstats.TargetMultiViewMigrationActivation(
        dataset_id="synthetic",
        final_gpu1_qualification_digest=values["final"],
        learning_control_report_digest=values["learning"],
        size_fidelity2_qualification_digest=values["fidelity"],
        migration_plan_digest=values["migration"],
        legacy_target_data_ladder_digest=values["legacy"],
        migrated_target_data_ladder_digest=values["ladder"],
        migrated_target_size_convergence_digest=values["convergence"],
        prior_target_production_corpus_digest=values["production"],
    )
    restored = mdstats.TargetMultiViewMigrationActivation.from_dict(receipt.to_dict())
    assert restored.content_digest == receipt.content_digest
    payload = receipt.to_dict()
    payload["status"] = "pending"
    payload.pop("content_digest")
    with pytest.raises(mdstats.TrainingDataInputError, match="terminally activated"):
        mdstats.TargetMultiViewMigrationActivation.from_dict(payload)


def test_campaign_store_atomic_replacement_deletes_stale_generation(tmp_path):
    from mdstats.training_data import campaign_cli

    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite3")
    store.put_records({
        "target_data_ladder": {"schema": "legacy", "generation": 4},
        "target_size_convergence": {"schema": "legacy", "generation": 2},
        "target_production_corpus_decision": {"schema": "legacy", "generation": 2},
    })
    store.replace_records_atomically(
        {
            "target_data_ladder_legacy_v4": {"schema": "legacy", "generation": 4},
            "target_data_ladder": {"schema": "migrated", "generation": 5},
            "target_size_convergence": {"schema": "migrated", "generation": 3},
            "target_multi_view_migration_activation": {"schema": "activation", "status": "activated"},
        },
        delete_keys=("target_production_corpus_decision", "prepare_restart_receipt"),
    )
    assert store.get_payload("target_data_ladder")["generation"] == 5
    assert store.get_payload("target_size_convergence")["generation"] == 3
    assert store.get_payload("target_data_ladder_legacy_v4")["generation"] == 4
    assert store.get_payload("target_multi_view_migration_activation")["status"] == "activated"
    assert store.get_payload_optional("target_production_corpus_decision") is None
    store.close()
