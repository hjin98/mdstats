from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats
from mdstats.training_data._common import digest


def _uid(i: int) -> str:
    return f"{i + 1:064x}"


def _unit(i: int) -> str:
    return f"{1000 + i:064x}"


def _evidence(size: int, score: float, *, stage: str, parent: mdstats.TargetSizeTrainingEvidence | None = None) -> mdstats.TargetSizeTrainingEvidence:
    epochs = {"coarse": 3, "short": 10, "final": 30}[stage]
    final = stage == "final"
    replay_value = None if stage == "coarse" else 20.0 + size
    return mdstats.TargetSizeTrainingEvidence(
        stage=stage, target_size=size, optimizer_seed=1, completed_epochs=epochs, planned_epochs=30,
        optimizer_update_count=epochs * 100, structures_presented=epochs * size,
        normalized_schedule_progress=1.0 if final else epochs / 30.0,
        instantaneous_learning_rate=1.0e-6 if final else 5.0e-5, wall_time_seconds=float(size),
        target_force_score_mev_per_a=score, numerical_valid=True, target_hard_gates_passed=True,
        foundation_identity_digest=digest({"foundation": 1}), evaluation_role_digest=digest({"evaluation": 1}),
        training_policy_digest=digest({"train2": 1}), training_run_digest=digest({"run": size}),
        checkpoint_digest=digest({"ckpt": stage, "size": size}), schedule_digest=digest({"schedule": 1}),
        optimizer_state_digest=digest({"optimizer": stage, "size": size}), rng_state_digest=digest({"rng": stage, "size": size}),
        target_evaluation_digest=digest({"target_eval": stage, "size": size}),
        replay_diagnostic_force_rmse_mev_per_a=replay_value,
        replay_evaluation_digest=None if replay_value is None else digest({"replay_eval": stage, "size": size}),
        replay_admissible=True if final else None, physical_qualification_passed=True if final else None,
        physical_qualification_digest=digest({"physical": size}) if final else None,
        parent_checkpoint_digest=None if parent is None else parent.checkpoint_digest,
        parent_optimizer_state_digest=None if parent is None else parent.optimizer_state_digest,
        parent_rng_state_digest=None if parent is None else parent.rng_state_digest,
    )


def _build_authorities():
    frames = tuple(_uid(i) for i in range(8))
    units = tuple(_unit(i) for i in range(4))
    intervals = tuple(
        mdstats.TargetDevelopmentInterval(
            unit_id=units[i],
            run_id=f"run-{i}",
            label_domain_id="target",
            condition_id=digest({"condition": i}),
            source_frame_start=2 * i,
            source_frame_stop=2 * i + 2,
            frame_uids=frames[2 * i : 2 * i + 2],
        )
        for i in range(4)
    )
    role_domain = mdstats.TargetDataDomainRoleFreeze(
        label_domain_id="target",
        outer_partition_digest=digest({"outer": 1}),
        cross_validation_plan_digest=digest({"cv": 1}),
        size_development_unit_ids=units,
        size_development_frame_uids=frames,
        final_validation_unit_ids=(),
        final_validation_frame_uids=(),
        uncertainty_calibration_unit_ids=(),
        uncertainty_calibration_frame_uids=(),
        locked_test_unit_ids=(),
        locked_test_frame_uids=(),
        purged_unit_ids=(),
        purged_frame_uids=(),
        excluded_unit_ids=(),
        excluded_frame_uids=(),
        cv_evaluation_unit_ids_by_fold=((0, units[:2]), (1, units[2:])),
        cv_checkpoint_monitor_unit_ids_by_fold=((0, ()), (1, ())),
        development_intervals=intervals,
    )
    role_freeze = mdstats.TargetDataRoleFreeze(
        dataset_id="synthetic",
        source_catalog_digest=digest({"sources": 1}),
        frame_catalog_digest=digest({"frames": 1}),
        data5_bundle_digest=digest({"data5": 1}),
        partition_policy_digest=digest({"partition_policy": 1}),
        partition_unit_catalog_digest=digest({"unit_catalog": 1}),
        leakage_audit_digest=digest({"leakage": 1}),
        policy=mdstats.TargetDataRoleFreezePolicy(),
        domains=(role_domain,),
        source_lineages=(),
        correlation_families=(),
    )

    frame_domain_digest = digest({
        "schema": "mdstats.foundation-audit-frame-domain.v1",
        "label_domain_id": "target",
        "frame_uids": list(frames),
    })
    metrics = mdstats.TargetModelAuditMetrics(
        configuration_count=8,
        atom_count=8,
        stress_configuration_count=0,
        energy_mae_ev_per_atom=0.01,
        force_component_rmse_ev_per_angstrom=0.02,
        stress_component_rmse_ev_per_angstrom3=None,
        species_macro_force_rmse_ev_per_angstrom=0.02,
        species_force_metrics=(mdstats.TargetModelSpeciesForceMetric(atomic_number=1, symbol="H", atom_count=8, component_rmse_ev_per_angstrom=0.02),),
        force_tail_metrics=(mdstats.TargetModelForceTailMetric(quantile=0.95, vector_error_ev_per_angstrom=0.03, component_abs_error_ev_per_angstrom=0.02),),
    )
    audit_domain = mdstats.FoundationAuditDomainRecord(
        label_domain_id="target",
        frame_uids=frames,
        frame_domain_digest=frame_domain_digest,
        training_difficulty_catalog_digest=digest({"difficulty": 1}),
        metrics=metrics,
    )
    audit = mdstats.FoundationTargetAudit(
        dataset_id="synthetic",
        source_catalog_digest=role_freeze.source_catalog_digest,
        frame_catalog_digest=role_freeze.frame_catalog_digest,
        data5_bundle_digest=role_freeze.data5_bundle_digest,
        data6_bundle_digest=digest({"data6": 1}),
        target_data_role_freeze_digest=role_freeze.content_digest,
        foundation_checkpoint_identity_digest=digest({"foundation_identity": 1}),
        foundation_checkpoint_sha256=digest({"foundation_bytes": 1}),
        model_sweep_checkpoint_digest=digest({"sweep": 1}),
        structural_provider_digests=(),
        policy=mdstats.TargetModelAuditPolicy(),
        domains=(audit_domain,),
        probe_contracts=(),
    )

    def family(family_id: str, kind: str):
        return mdstats.TargetCoverageFamilyReference(
            family_id=family_id,
            family_kind=kind,
            semantic_family=kind,
            required=True,
            metric="scaled_rms_l2",
            fidelity_diagnostic="wasserstein1",
            feature_names=("x",),
            frame_indices=tuple(range(8)),
            values=tuple((float(i),) for i in range(8)),
            weights=(0.125,) * 8,
            scales=(1.0,),
            local_radii=(1.0,) * 8,
            extent_channels=(),
            source_evidence_digest=digest({"family": family_id}),
        )

    reference_domain = mdstats.TargetCoverageDomainReference(
        label_domain_id="target",
        frame_uids=frames,
        families=(family("target_label:global", "target_label"), family("foundation_residual:global", "foundation_residual")),
        strata=(),
        frame_domain_digest=frame_domain_digest,
    )
    reference = mdstats.TargetCoverageReference(
        dataset_id="synthetic",
        source_catalog_digest=role_freeze.source_catalog_digest,
        frame_catalog_digest=role_freeze.frame_catalog_digest,
        data4_bundle_digest=digest({"data4": 1}),
        data5_bundle_digest=role_freeze.data5_bundle_digest,
        data6_bundle_digest=audit.data6_bundle_digest,
        target_data_role_freeze_digest=role_freeze.content_digest,
        foundation_target_audit_digest=audit.content_digest,
        policy=mdstats.TargetCoveragePolicy(),
        domains=(reference_domain,),
    )

    entries = tuple(
        mdstats.TargetDataLadderEntry(rank=i, frame_uid=uid, primary_reason="hierarchical_fused_fps", reason_codes=("hierarchical_fused_fps",))
        for i, uid in enumerate(frames)
    )
    rungs = []
    for size, mass in ((2, 0.96), (4, 0.98), (8, 1.0)):
        selected = frames[:size]
        reports = tuple(
            mdstats.TargetCoverageFamilyReport(
                family_id=fam.family_id,
                required=True,
                reference_element_count=8,
                representative_element_count=size,
                covered_reference_mass=mass,
                threshold=0.95,
                coverage_passed=True,
                extent_passed=True,
                extent_failures=(),
                fidelity_diagnostic="wasserstein1",
                fidelity_value=max(0.0, 1.0 - mass),
            )
            for fam in reference_domain.families
        )
        coverage = mdstats.TargetCoverageReport(
            reference_digest=reference.content_digest,
            label_domain_id="target",
            selected_frame_uids=selected,
            family_reports=reports,
            stratum_reports=(),
            passed=True,
        )
        rungs.append(mdstats.TargetDataLadderRung(
            target_size=size,
            materializable=True,
            frame_uids=selected,
            coverage_report=coverage,
            mandatory_obligations_passed=True,
            unsatisfied_obligation_ids=(),
        ))
    ladder_domain = mdstats.TargetDataLadderDomainPlan(
        label_domain_id="target",
        reference_domain_digest=reference_domain.content_digest,
        role_domain_digest=role_domain.content_digest,
        pool_frame_count=8,
        required_family_ids=tuple(f.family_id for f in reference_domain.families),
        semantic_family_ids=("foundation_residual", "target_label"),
        mandatory_obligation_count=0,
        mandatory_reserved_count=0,
        unsatisfied_obligation_ids_at_largest_rung=(),
        master_order=entries,
        rungs=tuple(rungs),
    )
    ladder_policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(1, 2, 3), minimum_materializable_rungs=3)
    qualifications = tuple(
        mdstats.TargetDataLadderRungQualification(
            target_size=rung.target_size,
            qualified=True,
            domain_coverage_passed=(("target", True),),
            domain_mandatory_passed=(("target", True),),
            coverage_report_digests=(("target", rung.coverage_report.content_digest),),
        )
        for rung in rungs
    )
    ladder = mdstats.TargetDataLadderPlan(
        dataset_id="synthetic",
        target_coverage_reference_digest=reference.content_digest,
        target_data_role_freeze_digest=role_freeze.content_digest,
        policy=ladder_policy,
        domains=(ladder_domain,),
        configured_candidate_sizes=ladder_policy.target_sizes,
        materialized_target_sizes=ladder_policy.target_sizes,
        rung_qualifications=qualifications,
        stage_a_survivor_limit=4,
        last_materialized_target_size=8,
        materialization_stop_reason="all_materializable_rungs_materialized",
        authority_version=mdstats.TARGET_DATA_LADDER_VERSION,
    )
    convergence = mdstats.build_target_size_convergence_plan(ladder)
    coarse = tuple(_evidence(size, score, stage="coarse") for size, score in ((2, 10.0), (4, 10.5), (8, 20.0)))
    convergence = mdstats.with_stage_b0_evidence(convergence, coarse)
    coarse_by_size = {item.target_size: item for item in convergence.coarse_training_evidence}
    short = tuple(_evidence(size, score, stage="short", parent=coarse_by_size[size]) for size, score in ((2, 10.0), (4, 10.5), (8, 20.0)))
    convergence = mdstats.with_stage_b_evidence(convergence, short)
    assert convergence.stage_b_finalist_sizes == (2, 4)
    short_by_size = {item.target_size: item for item in convergence.short_training_evidence}
    convergence = mdstats.with_stage_c_evidence(
        convergence,
        (_evidence(2, 8.9, stage="final", parent=short_by_size[2]), _evidence(4, 8.1, stage="final", parent=short_by_size[4])),
        largest_materialized_size=8,
    )
    assert convergence.outcome == "selected" and convergence.selected_target_size == 2
    return role_freeze, audit, reference, ladder, convergence


def test_target_data2e_freezes_exact_selected_membership_and_full_provenance():
    role, audit, reference, ladder, convergence = _build_authorities()
    decision = mdstats.build_target_production_corpus_decision(
        target_data_role_freeze=role,
        foundation_target_audit=audit,
        target_coverage_reference=reference,
        target_data_ladder=ladder,
        target_size_convergence=convergence,
    )
    assert decision.selected_target_size == 2
    assert decision.bounded_ladder_converged
    assert decision.target_size_convergence_digest == convergence.content_digest
    assert decision.coverage_policy.coverage_threshold == 0.95
    assert decision.coverage_policy.coverage_resolution_mass == pytest.approx(1 / 128)
    domain = decision.domain("target")
    assert domain.frame_uids == ladder.domain("target").rungs[0].frame_uids
    assert domain.selected_coverage_report.passed
    assert len(domain.rung_provenance) == 3
    assert dict(domain.foundation_residual_family_reference_digests)
    assert {item.stage for item in decision.equivalence_comparisons} == {"final"}
    assert any(item.practically_equivalent for item in decision.equivalence_comparisons if item.stage == "final")


def test_target_data2e_round_trip_and_live_validation_are_exact():
    role, audit, reference, ladder, convergence = _build_authorities()
    decision = mdstats.build_target_production_corpus_decision(
        target_data_role_freeze=role,
        foundation_target_audit=audit,
        target_coverage_reference=reference,
        target_data_ladder=ladder,
        target_size_convergence=convergence,
    )
    restored = mdstats.TargetProductionCorpusDecision.from_dict(decision.to_dict())
    assert restored.content_digest == decision.content_digest
    mdstats.validate_target_production_corpus_decision(
        restored,
        target_data_role_freeze=role,
        foundation_target_audit=audit,
        target_coverage_reference=reference,
        target_data_ladder=ladder,
        target_size_convergence=convergence,
    )


def test_target_data2e_refuses_waiting_nonconverged_and_failed_funnels():
    role, audit, reference, ladder, selected = _build_authorities()
    waiting = mdstats.build_target_size_convergence_plan(ladder)
    with pytest.raises(mdstats.TargetProductionCorpusDecisionError, match="requires a completed"):
        mdstats.build_target_production_corpus_decision(
            target_data_role_freeze=role, foundation_target_audit=audit,
            target_coverage_reference=reference, target_data_ladder=ladder,
            target_size_convergence=waiting,
        )
    nonconverged = replace(selected, selected_target_size=None, outcome="nonconverged_at_ladder_boundary", decision_reason="boundary still improving")
    with pytest.raises(mdstats.TargetProductionCorpusDecisionError, match="current outcome"):
        mdstats.build_target_production_corpus_decision(
            target_data_role_freeze=role, foundation_target_audit=audit,
            target_coverage_reference=reference, target_data_ladder=ladder,
            target_size_convergence=nonconverged,
        )


def test_target_data2e_detects_stale_upstream_authority():
    role, audit, reference, ladder, convergence = _build_authorities()
    decision = mdstats.build_target_production_corpus_decision(
        target_data_role_freeze=role, foundation_target_audit=audit,
        target_coverage_reference=reference, target_data_ladder=ladder,
        target_size_convergence=convergence,
    )
    stale = replace(convergence, decision_reason=convergence.decision_reason + " changed")
    with pytest.raises(mdstats.TargetProductionCorpusDecisionError, match="stale|differs"):
        mdstats.validate_target_production_corpus_decision(
            decision,
            target_data_role_freeze=role, foundation_target_audit=audit,
            target_coverage_reference=reference, target_data_ladder=ladder,
            target_size_convergence=stale,
        )
