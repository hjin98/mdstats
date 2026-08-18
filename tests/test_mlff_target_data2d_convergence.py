from __future__ import annotations

import pytest

import mdstats
from mdstats.training_data._common import digest


def _uid(i: int) -> str:
    return f"{i + 1:064x}"


def _report(size: int, passed: bool, *, domain: str = "target") -> mdstats.TargetCoverageReport:
    frames = tuple(_uid(i) for i in range(size))
    family = mdstats.TargetCoverageFamilyReport(
        family_id="geometry", required=True, reference_element_count=64,
        representative_element_count=size, covered_reference_mass=0.99 if passed else 0.90,
        threshold=0.95, coverage_passed=passed, extent_passed=passed,
        extent_failures=() if passed else ("q01",), fidelity_diagnostic="wasserstein1", fidelity_value=0.01,
    )
    return mdstats.TargetCoverageReport(
        reference_digest="a" * 64, label_domain_id=domain, selected_frame_uids=frames,
        family_reports=(family,), stratum_reports=(), passed=passed,
    )


def _ladder(*, first_qualified_size: int = 2, second_domain_first_qualified_size: int | None = None):
    exponents = (1, 2, 3, 4, 5)
    sizes = tuple(1 << v for v in exponents)
    entries = tuple(
        mdstats.TargetDataLadderEntry(
            rank=i, frame_uid=_uid(i), primary_reason="hierarchical_fused_fps",
            reason_codes=("hierarchical_fused_fps",),
        ) for i in range(max(sizes))
    )

    def domain(name: str, threshold: int):
        rungs = []
        for size in sizes:
            passed = size >= threshold
            rungs.append(mdstats.TargetDataLadderRung(
                target_size=size, materializable=True, frame_uids=tuple(_uid(i) for i in range(size)),
                coverage_report=_report(size, passed, domain=name), mandatory_obligations_passed=True,
            ))
        return mdstats.TargetDataLadderDomainPlan(
            label_domain_id=name, reference_domain_digest=digest({"ref": name}), role_domain_digest=digest({"role": name}),
            pool_frame_count=max(sizes), required_family_ids=("geometry",), semantic_family_ids=("geometry",),
            mandatory_obligation_count=1, mandatory_reserved_count=1, unsatisfied_obligation_ids_at_largest_rung=(),
            master_order=entries, rungs=tuple(rungs),
        )

    thresholds = {"target": first_qualified_size}
    if second_domain_first_qualified_size is not None:
        thresholds["target2"] = second_domain_first_qualified_size
    domains = tuple(domain(name, threshold) for name, threshold in thresholds.items())
    qualifications = []
    for size in sizes:
        cov = tuple((name, size >= threshold) for name, threshold in thresholds.items())
        reports = tuple((name, _report(size, size >= threshold, domain=name).content_digest) for name, threshold in thresholds.items())
        qualifications.append(mdstats.TargetDataLadderRungQualification(
            target_size=size, qualified=all(v for _, v in cov), domain_coverage_passed=cov,
            domain_mandatory_passed=tuple((name, True) for name in thresholds), coverage_report_digests=reports,
        ))
    return mdstats.TargetDataLadderPlan(
        dataset_id="synthetic", target_coverage_reference_digest="b" * 64, target_data_role_freeze_digest="c" * 64,
        policy=mdstats.TargetDataLadderPolicy(ladder_exponents=exponents, minimum_materializable_rungs=3), domains=domains,
        configured_candidate_sizes=sizes, materialized_target_sizes=sizes, rung_qualifications=tuple(qualifications),
        unavailable_target_sizes=(), last_materialized_target_size=max(sizes),
        materialization_stop_reason="all_materializable_rungs_materialized", authority_version=mdstats.TARGET_DATA_LADDER_VERSION,
    )


def _ev(
    size: int, score: float, *, stage: str, parent: mdstats.TargetSizeTrainingEvidence | None = None,
    replay: float | None = None, numerical: bool = True, target_gate: bool = True,
    replay_ok: bool | None = None, physical_ok: bool | None = None,
) -> mdstats.TargetSizeTrainingEvidence:
    epochs = {"coarse": 3, "short": 10, "final": 30}[stage]
    final = stage == "final"
    if stage == "coarse" and replay is not None:
        raise ValueError("coarse helper is target-only")
    return mdstats.TargetSizeTrainingEvidence(
        stage=stage, target_size=size, optimizer_seed=1, completed_epochs=epochs, planned_epochs=30,
        optimizer_update_count=epochs * 100, structures_presented=epochs * size,
        normalized_schedule_progress=1.0 if final else epochs / 30.0,
        instantaneous_learning_rate=1.0e-6 if final else 5.0e-5, wall_time_seconds=float(size),
        target_force_score_mev_per_a=score, numerical_valid=numerical, target_hard_gates_passed=target_gate,
        foundation_identity_digest=digest({"foundation": 1}), evaluation_role_digest=digest({"evaluation_role": 1}),
        training_policy_digest=digest({"train2_policy": 1}), training_run_digest=digest({"run": size}),
        checkpoint_digest=digest({"ckpt": stage, "size": size}), schedule_digest=digest({"schedule": 1}),
        optimizer_state_digest=digest({"opt": stage, "size": size}), rng_state_digest=digest({"rng": stage, "size": size}),
        target_evaluation_digest=digest({"target": stage, "size": size}),
        replay_diagnostic_force_rmse_mev_per_a=replay,
        replay_evaluation_digest=(digest({"replay": stage, "size": size}) if replay is not None or final else None),
        replay_admissible=replay_ok, physical_qualification_passed=physical_ok,
        physical_qualification_digest=digest({"physical": size}) if final else None,
        parent_checkpoint_digest=None if parent is None else parent.checkpoint_digest,
        parent_optimizer_state_digest=None if parent is None else parent.optimizer_state_digest,
        parent_rng_state_digest=None if parent is None else parent.rng_state_digest,
    )


def _coarse(plan, scores: dict[int, float]):
    evidence = tuple(_ev(size, scores[size], stage="coarse") for size in plan.stage_a_survivor_sizes)
    return mdstats.with_stage_b0_evidence(plan, evidence)


def _short(plan, scores: dict[int, float], *, replay: float | None = None):
    coarse = {x.target_size: x for x in plan.coarse_training_evidence}
    evidence = tuple(_ev(size, scores[size], stage="short", parent=coarse[size], replay=replay) for size in plan.stage_b_survivor_sizes)
    return mdstats.with_stage_b_evidence(plan, evidence)


def test_hard_coverage_retains_every_qualified_rung():
    plan = mdstats.build_target_size_convergence_plan(_ladder(first_qualified_size=2))
    assert plan.stage_a_survivor_sizes == (2, 4, 8, 16, 32)
    assert plan.outcome == "awaiting_stage_b0_coarse_training"


def test_hard_coverage_is_global_across_label_domains():
    plan = mdstats.build_target_size_convergence_plan(_ladder(first_qualified_size=2, second_domain_first_qualified_size=8))
    assert plan.stage_a_survivor_sizes == (8, 16, 32)


def test_hard_coverage_fails_with_fewer_than_three_qualifiers():
    with pytest.raises(mdstats.TargetDataCoverageError, match="fewer than 3"):
        mdstats.build_target_size_convergence_plan(_ladder(first_qualified_size=16))


def test_epoch3_screen_reduces_all_qualifiers_to_four():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10.0, 4: 9.0, 8: 8.0, 16: 7.0, 32: 20.0})
    assert set(plan.stage_b_survivor_sizes) == {2, 4, 8, 16}
    assert plan.outcome == "awaiting_stage_b1_short_training"


def test_epoch3_boundary_is_preserved_inside_practical_equivalence_band():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10.0, 4: 10.1, 8: 10.2, 16: 10.3, 32: 10.8})
    assert 32 in plan.stage_b_survivor_sizes
    assert 16 not in plan.stage_b_survivor_sizes


def test_epoch3_boundary_can_be_eliminated_when_materially_worse():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10.0, 4: 10.1, 8: 10.2, 16: 10.3, 32: 15.0})
    assert 32 not in plan.stage_b_survivor_sizes


def test_epoch3_is_target_only():
    with pytest.raises(mdstats.TrainingDataInputError, match="target-only"):
        mdstats.TargetSizeTrainingEvidence(
            stage="coarse", target_size=2, optimizer_seed=1, completed_epochs=3, planned_epochs=30,
            optimizer_update_count=10, structures_presented=20, normalized_schedule_progress=0.1,
            instantaneous_learning_rate=1e-4, wall_time_seconds=1.0, target_force_score_mev_per_a=10.0,
            numerical_valid=True, target_hard_gates_passed=True, foundation_identity_digest=digest({"f": 1}),
            evaluation_role_digest=digest({"e": 1}), training_policy_digest=digest({"p": 1}),
            training_run_digest=digest({"r": 1}), checkpoint_digest=digest({"c": 1}),
            schedule_digest=digest({"s": 1}), optimizer_state_digest=digest({"o": 1}), rng_state_digest=digest({"g": 1}),
            target_evaluation_digest=digest({"t": 1}), replay_diagnostic_force_rmse_mev_per_a=1.0,
            replay_evaluation_digest=digest({"re": 1}),
        )


def test_epoch10_continues_exact_epoch3_state_and_reduces_to_two():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10, 4: 9, 8: 8, 16: 7, 32: 20})
    plan = _short(plan, {2: 9.0, 4: 8.0, 8: 7.0, 16: 6.0})
    assert set(plan.stage_b_finalist_sizes) == {8, 16}
    assert plan.outcome == "awaiting_stage_c_full_training"


def test_epoch10_rejects_rng_ancestry_mismatch():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10, 4: 9, 8: 8, 16: 7, 32: 20})
    coarse = {x.target_size: x for x in plan.coarse_training_evidence}
    evidence = []
    for size in plan.stage_b_survivor_sizes:
        item = _ev(size, float(size), stage="short", parent=coarse[size])
        payload = item.to_dict(); payload.pop("content_digest")
        if size == plan.stage_b_survivor_sizes[0]:
            payload["parent_rng_state_digest"] = digest({"wrong": 1})
        evidence.append(mdstats.TargetSizeTrainingEvidence.from_dict(payload))
    with pytest.raises(mdstats.TrainingDataInputError, match="RNG ancestry|continuation ancestry"):
        mdstats.with_stage_b_evidence(plan, evidence)


def test_epoch10_boundary_preservation_and_replay_has_zero_ranking_credit():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10.0, 4: 10.1, 8: 10.2, 16: 20.0, 32: 10.8})
    assert 32 in plan.stage_b_survivor_sizes
    coarse = {x.target_size: x for x in plan.coarse_training_evidence}
    scores = {size: 10.0 + i * 0.1 for i, size in enumerate(plan.stage_b_survivor_sizes)}
    evidence = tuple(_ev(size, scores[size], stage="short", parent=coarse[size], replay=1000.0 if size == 32 else 0.1) for size in plan.stage_b_survivor_sizes)
    plan = mdstats.with_stage_b_evidence(plan, evidence)
    assert 32 in plan.stage_b_finalist_sizes


def test_final_within_equivalence_prefers_smaller_and_replay_is_hard_gate_only():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10, 4: 9, 8: 8, 16: 7, 32: 30})
    plan = _short(plan, {2: 8, 4: 7, 8: 6, 16: 5})
    short = {x.target_size: x for x in plan.short_training_evidence}
    a, b = sorted(plan.stage_b_finalist_sizes)
    final = (
        _ev(a, 8.9, stage="final", parent=short[a], replay=100.0, replay_ok=True, physical_ok=True),
        _ev(b, 8.1, stage="final", parent=short[b], replay=1.0, replay_ok=True, physical_ok=True),
    )
    result = mdstats.with_stage_c_evidence(plan, final, largest_materialized_size=32)
    assert result.outcome == "selected"
    assert result.selected_target_size == a


def test_final_replay_and_physical_gates_are_hard():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 10, 4: 9, 8: 8, 16: 7, 32: 30})
    plan = _short(plan, {2: 8, 4: 7, 8: 6, 16: 5})
    short = {x.target_size: x for x in plan.short_training_evidence}
    a, b = plan.stage_b_finalist_sizes
    result = mdstats.with_stage_c_evidence(plan, (
        _ev(a, 5.0, stage="final", parent=short[a], replay_ok=False, physical_ok=True),
        _ev(b, 7.0, stage="final", parent=short[b], replay_ok=True, physical_ok=True),
    ), largest_materialized_size=32)
    assert result.selected_target_size == b


def test_boundary_materially_better_at_epoch30_reports_nonconvergence():
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    plan = _coarse(plan, {2: 20, 4: 19, 8: 18, 16: 17, 32: 10})
    plan = _short(plan, {size: (5.0 if size == 32 else 10.0 + size) for size in plan.stage_b_survivor_sizes})
    assert 32 in plan.stage_b_finalist_sizes
    short = {x.target_size: x for x in plan.short_training_evidence}
    other = next(v for v in plan.stage_b_finalist_sizes if v != 32)
    result = mdstats.with_stage_c_evidence(plan, (
        _ev(other, 10.0, stage="final", parent=short[other], replay_ok=True, physical_ok=True),
        _ev(32, 7.0, stage="final", parent=short[32], replay_ok=True, physical_ok=True),
    ))
    assert result.outcome == "nonconverged_at_ladder_boundary"


def test_round_trip_and_live_ladder_validation():
    ladder = _ladder()
    plan = mdstats.build_target_size_convergence_plan(ladder)
    plan = _coarse(plan, {2: 10, 4: 9, 8: 8, 16: 7, 32: 20})
    restored = mdstats.TargetSizeConvergencePlan.from_dict(plan.to_dict())
    assert restored.to_dict() == plan.to_dict()
    mdstats.validate_target_size_convergence_authority(restored, ladder=ladder)
