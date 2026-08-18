from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_ladder as tl
from mdstats.training_data._common import digest
from tests.test_mlff_target_data2c_ladder import _RoleDomain, _reference_and_role


def _always_qualifying_reference(n: int = 300):
    reference, role = _reference_and_role(n, with_strata=False)
    domain = reference.domain("target")
    families = tuple(replace(family, local_radii=np.full_like(family.local_radii, 1.0e9), extent_channels=()) for family in domain.families)
    return replace(reference, domains=(replace(domain, families=families, strata=()),)), role


def _policy() -> mdstats.TargetDataLadderPolicy:
    return mdstats.TargetDataLadderPolicy(
        ladder_exponents=(2, 3, 4, 5, 6, 7, 8), minimum_materializable_rungs=3,
        reserve_required_strata=False, reserve_correlation_intervals=False,
    )


def test_corrected_data2c_v3_materializes_every_globally_available_rung() -> None:
    reference, role = _always_qualifying_reference()
    plan = mdstats.build_target_data_ladder(reference, role, policy=_policy())
    assert plan.authority_version == mdstats.TARGET_DATA_LADDER_VERSION
    assert plan.to_dict()["schema"] == mdstats.TARGET_DATA_LADDER_PLAN_SCHEMA
    assert plan.configured_candidate_sizes == (4, 8, 16, 32, 64, 128, 256)
    assert plan.materialized_target_sizes == plan.configured_candidate_sizes
    assert plan.intentionally_unmaterialized_target_sizes == ()
    assert plan.early_stop_qualifying_sizes == ()
    assert plan.last_materialized_target_size == 256
    assert plan.materialization_stop_reason == "all_materializable_rungs_materialized"
    assert not plan.early_stopped
    assert len(plan.domain("target").master_order) == 256


def test_corrected_data2c_v3_preserves_exact_exhaustive_v1_science_for_all_rungs() -> None:
    reference, role = _always_qualifying_reference()
    policy = _policy()
    legacy = tl._build_target_data_ladder_exhaustive_v1(reference, role, policy=policy)
    current = mdstats.build_target_data_ladder(reference, role, policy=policy)
    v1 = legacy.domain("target")
    v3 = current.domain("target")
    for size in policy.target_sizes:
        before = next(item for item in v1.rungs if item.target_size == size)
        after = next(item for item in v3.rungs if item.target_size == size)
        assert before.frame_uids == after.frame_uids
        assert before.mandatory_obligations_passed == after.mandatory_obligations_passed
        assert before.unsatisfied_obligation_ids == after.unsatisfied_obligation_ids
        assert before.coverage_report is not None and after.coverage_report is not None
        assert before.coverage_report.content_digest == after.coverage_report.content_digest


def test_hard_coverage_admission_keeps_all_qualified_sizes_for_epoch3() -> None:
    reference, role = _always_qualifying_reference()
    ladder = mdstats.build_target_data_ladder(reference, role, policy=_policy())
    convergence = mdstats.build_target_size_convergence_plan(ladder)
    assert convergence.stage_a_survivor_sizes == ladder.materialized_target_sizes
    assert convergence.outcome == "awaiting_stage_b0_coarse_training"


def test_legacy_v1_remains_readable_but_is_stale_for_generated_campaigns() -> None:
    reference, role = _always_qualifying_reference()
    legacy = tl._build_target_data_ladder_exhaustive_v1(reference, role, policy=_policy())
    restored = mdstats.TargetDataLadderPlan.from_dict(legacy.to_dict())
    assert restored.authority_version == mdstats.TARGET_DATA_LADDER_LEGACY_VERSION
    with pytest.raises(mdstats.TrainingDataInputError, match="pre-v4 authority is stale"):
        mdstats.validate_target_data_ladder_authority(restored, reference=reference, target_data_role_freeze=role)


def test_v3_roundtrip_and_worker_count_are_scientifically_invariant() -> None:
    reference, role = _always_qualifying_reference()
    first = mdstats.build_target_data_ladder(reference, role, policy=_policy(), coverage_query_workers=1)
    second = mdstats.build_target_data_ladder(reference, role, policy=_policy(), coverage_query_workers=2)
    assert first.content_digest == second.content_digest
    assert first.to_dict() == second.to_dict()
    restored = mdstats.TargetDataLadderPlan.from_dict(first.to_dict())
    mdstats.validate_target_data_ladder_authority(restored, reference=reference, target_data_role_freeze=role)


def test_deprecated_stage_a_survivor_limit_has_no_scientific_effect() -> None:
    reference, role = _always_qualifying_reference()
    first = mdstats.build_target_data_ladder(reference, role, policy=_policy())
    second = mdstats.build_target_data_ladder(reference, role, policy=_policy(), stage_a_survivor_limit=5)
    assert first.content_digest == second.content_digest
    assert second.materialized_target_sizes == _policy().target_sizes


class _MultiRoleFreeze:
    def __init__(self, dataset_id: str, domains: tuple[_RoleDomain, ...], content_digest: str):
        self.dataset_id = dataset_id; self.domains = domains; self.content_digest = content_digest
        self._by_id = {item.label_domain_id: item for item in domains}
    def domain(self, label_domain_id: str):
        return self._by_id[label_domain_id]


def _two_domain_reference_and_role():
    reference, role = _reference_and_role(300, with_strata=False)
    first = reference.domain("target")
    second = replace(first, label_domain_id="target2", frame_domain_digest=digest({"domain": "target2"}))
    reference2 = replace(reference, domains=(first, second))
    role1 = role.domain("target")
    role2 = _RoleDomain("target2", role1.size_development_frame_uids, role1.development_intervals)
    return reference2, _MultiRoleFreeze(reference2.dataset_id, (role1, role2), reference2.target_data_role_freeze_digest)


def _fake_report(reference: mdstats.TargetCoverageReference, domain_id: str, selected, *, passed: bool):
    selected = tuple(selected)
    family = mdstats.TargetCoverageFamilyReport(
        family_id="synthetic:global-stop", required=True, reference_element_count=300,
        representative_element_count=len(selected), covered_reference_mass=1.0 if passed else 0.90,
        threshold=0.95, coverage_passed=passed, extent_passed=True, extent_failures=(),
        fidelity_diagnostic=None, fidelity_value=None,
    )
    return mdstats.TargetCoverageReport(
        reference_digest=reference.content_digest, label_domain_id=domain_id,
        selected_frame_uids=selected, family_reports=(family,), stratum_reports=(), passed=passed,
    )


def test_v4_full_ladder_and_any_rescue_are_global_across_label_domains() -> None:
    reference, role = _two_domain_reference_and_role()
    plan = mdstats.build_target_data_ladder(reference, role, policy=_policy())
    assert tuple(plan.materialized_target_sizes[: len(_policy().target_sizes)]) == _policy().target_sizes
    assert all(tuple(item.target_size for item in domain.materialized_rungs) == plan.materialized_target_sizes for domain in plan.domains)
    if plan.coverage_rescue_activated:
        assert tuple(size for size in plan.materialized_target_sizes if size not in _policy().target_sizes) == plan.coverage_rescue_candidate_sizes


def test_v3_fails_closed_if_observed_coverage_predicate_reverses(monkeypatch) -> None:
    reference, role = _always_qualifying_reference()

    def fake_nested(ref, domain_id, subsets, *, query_workers=1):
        del query_workers
        reports = []
        for selected in subsets:
            # pass at 4, fail at 8, then pass again: impossible for the exact
            # monotone hard-coverage contract and therefore invalid evidence.
            passed = len(selected) == 4 or len(selected) >= 16
            reports.append(_fake_report(ref, domain_id, selected, passed=passed))
        return tuple(reports)

    monkeypatch.setattr(tl, "score_target_nested_subsets_coverage", fake_nested)
    with pytest.raises(mdstats.TrainingDataInputError, match="monot|revers"):
        mdstats.build_target_data_ladder(reference, role, policy=_policy())
