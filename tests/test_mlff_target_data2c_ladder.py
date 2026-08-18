from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_coverage as tc
from mdstats.training_data._common import digest


class _Unit:
    def __init__(self, unit_id: str):
        self.unit_id = unit_id


class _UnitCatalog:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def unit_for_frame(self, frame_uid: str) -> _Unit:
        return _Unit(self.mapping[frame_uid])


class _Data5:
    def __init__(self, mapping: dict[str, str]):
        self.unit_catalog = _UnitCatalog(mapping)


def _uid(index: int) -> str:
    return f"{index + 1:064x}"


@dataclass(frozen=True)
class _Interval:
    unit_id: str
    frame_uids: tuple[str, ...]


class _RoleDomain:
    def __init__(self, label_domain_id: str, frame_uids: tuple[str, ...], intervals: tuple[_Interval, ...]):
        self.label_domain_id = label_domain_id
        self.size_development_frame_uids = frame_uids
        self.development_intervals = intervals
        self.content_digest = digest({
            "label_domain_id": label_domain_id,
            "frames": frame_uids,
            "intervals": [(item.unit_id, item.frame_uids) for item in intervals],
        })


class _RoleFreeze:
    def __init__(self, dataset_id: str, domain: _RoleDomain, content_digest: str):
        self.dataset_id = dataset_id
        self.domains = (domain,)
        self.content_digest = content_digest
        self._domain = domain

    def domain(self, label_domain_id: str):
        if label_domain_id != self._domain.label_domain_id:
            raise KeyError(label_domain_id)
        return self._domain


def _reference_and_role(n: int, *, with_strata: bool = True):
    frame_uids = tuple(_uid(i) for i in range(n))
    unit_ids = tuple(f"unit-{i // 5}" for i in range(n))
    data5 = _Data5(dict(zip(frame_uids, unit_ids, strict=True)))
    policy = mdstats.TargetCoveragePolicy(
        require_condition_support=False,
        require_structural_event_support=False,
        require_profile_environment_support=False,
    )
    domain_index = {uid: i for i, uid in enumerate(frame_uids)}
    x = np.linspace(-2.0, 2.0, n)
    family1 = tc._build_family(
        family_id="structural:geometry",
        family_kind="structural",
        semantic_family="geometry",
        feature_names=("x", "x2"),
        frame_uids=frame_uids,
        values=np.column_stack((x, x * x)),
        domain_frame_index=domain_index,
        data5_bundle=data5,
        policy=policy,
        source_evidence_digest="a" * 64,
        required=True,
        extent=True,
    )
    family2 = tc._build_family(
        family_id="foundation_residual:global",
        family_kind="foundation_residual",
        semantic_family="foundation_weakness",
        feature_names=("residual",),
        frame_uids=frame_uids,
        values=np.abs(x)[:, None],
        domain_frame_index=domain_index,
        data5_bundle=data5,
        policy=policy,
        source_evidence_digest="b" * 64,
        required=True,
        extent=True,
    )
    assert family1 is not None and family2 is not None
    strata = ()
    if with_strata:
        strata = (
            mdstats.TargetCoverageStratumRequirement(
                stratum_id="rare:left",
                stratum_kind="rare_structural_event",
                label="left-tail",
                frame_indices=(0, 1),
                minimum_selected_frames=1,
                required=True,
            ),
            mdstats.TargetCoverageStratumRequirement(
                stratum_id="rare:right",
                stratum_kind="rare_structural_event",
                label="right-tail",
                frame_indices=(n - 2, n - 1),
                minimum_selected_frames=1,
                required=True,
            ),
        )
    domain = mdstats.TargetCoverageDomainReference(
        label_domain_id="target",
        frame_uids=frame_uids,
        families=(family1, family2),
        strata=strata,
        frame_domain_digest="c" * 64,
    )
    role_digest = "6" * 64
    reference = mdstats.TargetCoverageReference(
        dataset_id="synthetic",
        source_catalog_digest="1" * 64,
        frame_catalog_digest="2" * 64,
        data4_bundle_digest="3" * 64,
        data5_bundle_digest="4" * 64,
        data6_bundle_digest="5" * 64,
        target_data_role_freeze_digest=role_digest,
        foundation_target_audit_digest="7" * 64,
        policy=policy,
        domains=(domain,),
    )
    intervals = tuple(
        _Interval(
            unit_id=f"{1000 + block:064x}",
            frame_uids=frame_uids[first : min(n, first + 5)],
        )
        for block, first in enumerate(range(0, n, 5))
    )
    role_domain = _RoleDomain("target", frame_uids, intervals)
    role = _RoleFreeze("synthetic", role_domain, role_digest)
    return reference, role


def test_default_target_data2c_ladder_is_fixed_2pow7_through_2pow13() -> None:
    policy = mdstats.TargetDataLadderPolicy()
    assert policy.ladder_exponents == (7, 8, 9, 10, 11, 12, 13)
    assert policy.target_sizes == (128, 256, 512, 1024, 2048, 4096, 8192)
    assert policy.minimum_materializable_rungs == 3


def test_target_data2c_builds_one_exact_nested_master_prefix_and_round_trips() -> None:
    reference, role = _reference_and_role(40)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4, 5), minimum_materializable_rungs=3)
    first = mdstats.build_target_data_ladder(reference, role, policy=policy)
    second = mdstats.build_target_data_ladder(reference, role, policy=policy)
    assert first.content_digest == second.content_digest
    domain = first.domain("target")
    assert [item.target_size for item in domain.rungs] == [4, 8, 16, 32]
    assert all(item.materializable for item in domain.rungs)
    order = tuple(item.frame_uid for item in domain.master_order)
    for rung in domain.rungs:
        assert rung.frame_uids == order[: rung.target_size]
        assert rung.coverage_report is not None
        assert set(rung.coverage_report.selected_frame_uids) == set(rung.frame_uids)
    mdstats.assert_nested_coverage_monotonicity(
        tuple(item.coverage_report for item in domain.rungs if item.coverage_report is not None)
    )
    restored = mdstats.TargetDataLadderPlan.from_dict(first.to_dict())
    assert restored.content_digest == first.content_digest


def test_target_data2c_quota_first_frontloads_required_strata_and_intervals() -> None:
    reference, role = _reference_and_role(20)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4), minimum_materializable_rungs=3)
    plan = mdstats.build_target_data_ladder(reference, role, policy=policy)
    domain = plan.domain("target")
    # Four correlation intervals plus two tail strata can be covered by the
    # four interval anchors because the tail strata overlap the end intervals.
    first_four = set(item.frame_uid for item in domain.master_order[:4])
    assert first_four & set(reference.domain("target").frame_uids[:2])
    assert first_four & set(reference.domain("target").frame_uids[-2:])
    for interval in role.domain("target").development_intervals:
        assert first_four & set(interval.frame_uids)
    assert all(item.primary_reason == "mandatory_quota" for item in domain.master_order[:4])
    assert domain.mandatory_obligation_count == 6
    assert domain.unsatisfied_obligation_ids_at_largest_rung == ()


def test_target_data2c_unavailable_rungs_are_explicit_not_fabricated() -> None:
    reference, role = _reference_and_role(20, with_strata=False)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4, 5), minimum_materializable_rungs=3)
    domain = mdstats.build_target_data_ladder(reference, role, policy=policy).domain("target")
    assert [item.materializable for item in domain.rungs] == [True, True, True, False]
    unavailable = domain.rungs[-1]
    assert unavailable.target_size == 32
    assert unavailable.frame_uids == ()
    assert unavailable.coverage_report is None
    assert "authorized_pool_has_20_frames" in unavailable.unavailable_reason


def test_target_data2c_fails_closed_when_fewer_than_three_rungs_can_exist() -> None:
    reference, role = _reference_and_role(10, with_strata=False)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4), minimum_materializable_rungs=3)
    with pytest.raises(mdstats.TrainingDataInputError, match="at least 3 materializable rungs"):
        mdstats.build_target_data_ladder(reference, role, policy=policy)


def test_target_data2c_policy_identity_changes_when_ladder_changes() -> None:
    first = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4))
    second = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 5))
    assert first.policy_digest != second.policy_digest


def test_target_data2c_authority_fails_closed_when_reference_changes() -> None:
    reference, role = _reference_and_role(20, with_strata=False)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4), minimum_materializable_rungs=3)
    plan = mdstats.build_target_data_ladder(reference, role, policy=policy)
    stale = SimpleNamespace(
        dataset_id=reference.dataset_id,
        content_digest="9" * 64,
        domains=reference.domains,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="target coverage reference changed"):
        mdstats.validate_target_data_ladder_authority(
            plan,
            reference=stale,
            target_data_role_freeze=role,
        )


def test_target_data2c_is_bound_into_prepare_restart_and_preflight_contract() -> None:
    from mdstats.training_data import campaign_cli

    assert "target_data_ladder" in campaign_cli._PREPARE_RECEIPT_RECORD_KEYS
    contract = campaign_cli._prepare_contract_signature()
    assert contract["target_data2c_ladder_version"] == mdstats.TARGET_DATA_LADDER_VERSION
    assert callable(campaign_cli._load_verified_target_data_ladder_authority)
    assert callable(campaign_cli._ensure_target_data_ladder)


def test_target_data2c_campaign_authority_persists_and_reuses_without_rebuild(tmp_path, monkeypatch) -> None:
    from mdstats.training_data import campaign_cli
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path / "inputs")
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite")
    store.put_record("target_data_role_freeze", freeze)
    cfg = {"target_data": {"size_convergence": {"ladder_exponents": [2, 3, 4, 5], "minimum_materializable_rungs": 3}}}
    first = campaign_cli._ensure_target_data_ladder(store, cfg=cfg, coverage_reference=reference)
    restored = store.get_record("target_data_ladder", mdstats.TargetDataLadderPlan)
    assert restored.content_digest == first.content_digest

    def unexpected(*args, **kwargs):  # pragma: no cover
        raise AssertionError("current TARGET-DATA2C authority should have been reused")

    monkeypatch.setattr(mdstats, "build_target_data_ladder", unexpected)
    second = campaign_cli._ensure_target_data_ladder(store, cfg=cfg, coverage_reference=reference)
    assert second.content_digest == first.content_digest


def test_target_data2c_builds_against_real_target_data2a_and_data2b_authorities(tmp_path) -> None:
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path / "inputs")
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4, 5), minimum_materializable_rungs=3)
    plan = mdstats.build_target_data_ladder(reference, freeze, policy=policy)
    mdstats.validate_target_data_ladder_authority(
        plan,
        reference=reference,
        target_data_role_freeze=freeze,
    )
    assert plan.target_coverage_reference_digest == reference.content_digest
    domain = plan.domains[0]
    assert domain.pool_frame_count == 36
    assert [item.target_size for item in domain.materialized_rungs] == [4, 8, 16, 32]
    # The 4-frame rung cannot span all eight DATA5 development intervals, but
    # the 8-frame and larger prefixes must do so because quota reservations are
    # front-loaded before FPS.
    assert not domain.materialized_rungs[0].mandatory_obligations_passed
    assert domain.materialized_rungs[1].mandatory_obligations_passed
    assert domain.materialized_rungs[-1].mandatory_obligations_passed


def _forced_ladder_qualification(size: int, rungs_by_domain, *, first_passing_size: int | None):
    coverage = []
    mandatory = []
    reports = []
    passed = first_passing_size is not None and size >= first_passing_size
    for domain_id in sorted(rungs_by_domain):
        rung = rungs_by_domain[domain_id]
        assert rung.coverage_report is not None
        coverage.append((domain_id, passed))
        mandatory.append((domain_id, True))
        reports.append((domain_id, rung.coverage_report.content_digest))
    return mdstats.TargetDataLadderRungQualification(
        target_size=size,
        qualified=passed,
        domain_coverage_passed=tuple(coverage),
        domain_mandatory_passed=tuple(mandatory),
        coverage_report_digests=tuple(reports),
        failure_reasons=() if passed else ("forced_test_coverage_failure",),
    )


def test_target_data2c_v4_activates_bounded_upper_ladder_rescue_only_when_needed(monkeypatch) -> None:
    from mdstats.training_data import target_ladder

    reference, role = _reference_and_role(64, with_strata=False)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4), minimum_materializable_rungs=3)

    monkeypatch.setattr(
        target_ladder,
        "_stage_a_qualification_for_rungs",
        lambda size, rungs: _forced_ladder_qualification(size, rungs, first_passing_size=32),
    )
    plan = mdstats.build_target_data_ladder(
        reference,
        role,
        policy=policy,
        minimum_coverage_qualifiers=3,
    )
    assert plan.coverage_rescue_activated is True
    assert plan.coverage_rescue_candidate_sizes == (24, 32, 40, 48, 56)
    assert plan.configured_candidate_sizes == (4, 8, 16, 24, 32, 40, 48, 56)
    assert max(plan.coverage_rescue_candidate_sizes) <= (7 * 64) // 8
    assert 64 - max(plan.coverage_rescue_candidate_sizes) >= 64 // 8
    convergence = mdstats.build_target_size_convergence_plan(plan)
    assert convergence.stage_a_survivor_sizes == (32, 40, 48, 56)
    restored = mdstats.TargetDataLadderPlan.from_dict(plan.to_dict())
    assert restored.content_digest == plan.content_digest
    assert restored.coverage_rescue_candidate_sizes == plan.coverage_rescue_candidate_sizes


def test_target_data2c_v4_does_not_expand_when_base_ladder_already_qualifies(monkeypatch) -> None:
    from mdstats.training_data import target_ladder

    reference, role = _reference_and_role(64, with_strata=False)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4), minimum_materializable_rungs=3)
    monkeypatch.setattr(
        target_ladder,
        "_stage_a_qualification_for_rungs",
        lambda size, rungs: _forced_ladder_qualification(size, rungs, first_passing_size=4),
    )
    plan = mdstats.build_target_data_ladder(reference, role, policy=policy, minimum_coverage_qualifiers=3)
    assert plan.coverage_rescue_activated is False
    assert plan.coverage_rescue_candidate_sizes == ()
    assert plan.configured_candidate_sizes == policy.target_sizes


def test_target_data2c_default_rescue_sizes_for_lta_scale_preserve_eval2_complement() -> None:
    from mdstats.training_data import target_ladder

    pool = 36_408
    policy = mdstats.TargetDataLadderPolicy()
    rescue = target_ladder._coverage_rescue_candidate_sizes(pool, policy)
    assert rescue == (13_568, 18_176, 22_656, 27_264, 31_744)
    assert rescue[0] > policy.target_sizes[-1]
    assert rescue[-1] <= (7 * pool) // 8
    assert pool - rescue[-1] >= pool // 8


def test_target_data2d_failure_reports_rescue_state_when_upper_ladder_still_insufficient(monkeypatch) -> None:
    from mdstats.training_data import target_ladder

    reference, role = _reference_and_role(64, with_strata=False)
    policy = mdstats.TargetDataLadderPolicy(ladder_exponents=(2, 3, 4), minimum_materializable_rungs=3)
    monkeypatch.setattr(
        target_ladder,
        "_stage_a_qualification_for_rungs",
        lambda size, rungs: _forced_ladder_qualification(size, rungs, first_passing_size=None),
    )
    plan = mdstats.build_target_data_ladder(reference, role, policy=policy, minimum_coverage_qualifiers=3)
    assert plan.coverage_rescue_activated is True
    with pytest.raises(mdstats.TargetDataCoverageError, match=r"coverage_rescue=active.*rescue_candidates=\[24, 32, 40, 48, 56\]"):
        mdstats.build_target_size_convergence_plan(plan)


def test_target_data2c_restart_rebuilds_when_rescue_qualifier_requirement_changes(tmp_path, monkeypatch) -> None:
    from mdstats.training_data import campaign_cli
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path / "inputs")
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite")
    store.put_record("target_data_role_freeze", freeze)
    cfg3 = {"target_data": {"size_convergence": {"ladder_exponents": [2, 3, 4, 5], "minimum_materializable_rungs": 3, "min_coverage_qualifiers": 3}}}
    first = campaign_cli._ensure_target_data_ladder(store, cfg=cfg3, coverage_reference=reference)
    assert first.coverage_rescue_min_qualifiers == 3

    original = mdstats.build_target_data_ladder
    observed = {}

    def wrapped(*args, **kwargs):
        observed["minimum"] = kwargs.get("minimum_coverage_qualifiers")
        return original(*args, **kwargs)

    monkeypatch.setattr(mdstats, "build_target_data_ladder", wrapped)
    cfg4 = {"target_data": {"size_convergence": {"ladder_exponents": [2, 3, 4, 5], "minimum_materializable_rungs": 3, "min_coverage_qualifiers": 4}}}
    second = campaign_cli._ensure_target_data_ladder(store, cfg=cfg4, coverage_reference=reference)
    assert observed["minimum"] == 4
    assert second.coverage_rescue_min_qualifiers == 4
    assert second.content_digest != first.content_digest
