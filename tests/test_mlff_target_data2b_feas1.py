from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_coverage as tc
from mdstats.training_data import target_coverage_feasibility as feas


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
    def __init__(self, frame_uids: tuple[str, ...], intervals: tuple[_Interval, ...]):
        self.label_domain_id = "target"
        self.size_development_frame_uids = frame_uids
        self.development_intervals = intervals


class _RoleFreeze:
    def __init__(self, domain: _RoleDomain, content_digest: str):
        self.dataset_id = "synthetic"
        self.content_digest = content_digest
        self._domain = domain

    def domain(self, label_domain_id: str):
        if label_domain_id != "target":
            raise KeyError(label_domain_id)
        return self._domain


def _reference_and_role(*, split_units: bool) -> tuple[mdstats.TargetCoverageReference, _RoleFreeze]:
    n = 16
    frame_uids = tuple(_uid(i) for i in range(n))
    # Pair neighboring frames geometrically.  In split-unit mode each pair is
    # split across units so own-unit exclusion retains one exact neighbor; in
    # grouped mode each pair shares a unit and cross-unit support vanishes.
    values = np.repeat(np.arange(n // 2, dtype=np.float64), 2)[:, None]
    unit_names = []
    for i in range(n):
        pair = i // 2
        unit_names.append(f"unit-{i % 2}" if split_units else f"unit-{pair}")
    mapping = dict(zip(frame_uids, unit_names, strict=True))
    data5 = _Data5(mapping)
    policy = mdstats.TargetCoveragePolicy(
        coverage_resolution_mass=0.05,
        coverage_threshold=0.95,
        require_condition_support=False,
        require_structural_event_support=False,
        require_profile_environment_support=False,
    )
    family = tc._build_family(
        family_id="target_label:paired",
        family_kind="target_label",
        semantic_family="paired",
        feature_names=("x",),
        frame_uids=frame_uids,
        values=values,
        domain_frame_index={uid: i for i, uid in enumerate(frame_uids)},
        data5_bundle=data5,
        policy=policy,
        source_evidence_digest="a" * 64,
        required=True,
        extent=True,
    )
    assert family is not None
    stratum = mdstats.TargetCoverageStratumRequirement(
        stratum_id="rare:first",
        stratum_kind="rare_structural_event",
        label="first",
        frame_indices=(0, 1),
        minimum_selected_frames=1,
        required=True,
    )
    domain = mdstats.TargetCoverageDomainReference(
        label_domain_id="target",
        frame_uids=frame_uids,
        families=(family,),
        strata=(stratum,),
        frame_domain_digest="b" * 64,
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
    by_unit: dict[str, list[str]] = {}
    for uid, unit in mapping.items():
        by_unit.setdefault(unit, []).append(uid)
    intervals = tuple(
        _Interval(unit_id=f"{1000 + i:064x}", frame_uids=tuple(sorted(uids)))
        for i, (_, uids) in enumerate(sorted(by_unit.items()))
    )
    return reference, _RoleFreeze(_RoleDomain(frame_uids, intervals), role_digest)


def test_feas1_is_deterministic_round_trippable_and_diagnostic_only() -> None:
    reference, role = _reference_and_role(split_units=True)
    first = mdstats.build_target_coverage_feasibility_report(reference, role, query_workers=1, query_block_size=3)
    second = mdstats.build_target_coverage_feasibility_report(reference, role, query_workers=2, query_block_size=7)
    assert first.content_digest == second.content_digest
    assert first.states == ("self_consistent", "optimization_required")
    domain = first.domains[0]
    family = domain.family_reports[0]
    assert family.self_excluded_support.zero_support_mass == pytest.approx(0.0)
    assert family.correlation_excluded_support.zero_support_mass == pytest.approx(0.0)
    assert family.optimistic_max_singleton_gain > 0.0
    assert 1 <= family.coverage_cardinality_lower_bound <= domain.candidate_frame_count
    assert domain.hard_obligation_slot_count >= 1 + len(role.domain("target").development_intervals)
    restored = mdstats.TargetCoverageFeasibilityReport.from_dict(first.to_dict())
    assert restored.content_digest == first.content_digest
    mdstats.validate_target_coverage_feasibility_authority(
        restored,
        target_coverage_reference=reference,
        target_data_role_freeze=role,
    )


def test_feas1_flags_cross_unit_fragility_without_failing_self_consistency() -> None:
    reference, role = _reference_and_role(split_units=False)
    report = mdstats.build_target_coverage_feasibility_report(reference, role)
    assert report.states == ("self_consistent", "cross_support_fragile")
    family = report.domains[0].family_reports[0]
    assert family.self_excluded_support.zero_support_mass == pytest.approx(0.0)
    assert family.correlation_excluded_support.zero_support_mass == pytest.approx(1.0)
    assert family.cross_support_fragile


def test_feas1_rejects_role_domain_drift() -> None:
    reference, role = _reference_and_role(split_units=True)
    broken = _RoleFreeze(
        _RoleDomain(reference.domain("target").frame_uids[:-1], role.domain("target").development_intervals),
        role.content_digest,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="frame-domain mismatch"):
        mdstats.build_target_coverage_feasibility_report(reference, broken)


def test_feas1_lower_bound_is_optimistic_and_capacity_state_is_fail_closed() -> None:
    gains = np.full(20_000, 1.0 / 20_000.0, dtype=np.float64)
    assert feas._coverage_cardinality_lower_bound(gains, 0.95) == 19_000
    assert feas._domain_state(fragile=False, lower_bound=16_385, ceiling=16_384) == (
        "self_consistent",
        "provably_capacity_infeasible",
    )



def test_feas1_vectorized_support_accumulation_is_bit_exact_to_scalar_order() -> None:
    rng = np.random.default_rng(20260817)
    degrees = rng.integers(0, 48, size=20_000, dtype=np.int64)
    weights = rng.random(20_000, dtype=np.float64)
    weights /= np.sum(weights, dtype=np.float64)
    scalar = feas._SupportAccumulator((2, 4, 8, 16, 32))
    for degree, weight in zip(degrees, weights, strict=True):
        scalar.add(int(degree), float(weight))
    vectorized = feas._SupportAccumulator((2, 4, 8, 16, 32))
    vectorized.add_many(degrees, weights)
    assert vectorized.freeze().to_dict() == scalar.freeze().to_dict()


def test_feas1_family_parallelism_is_scientifically_invariant() -> None:
    reference, role = _reference_and_role(split_units=True)
    first_family = reference.domains[0].families[0]
    second_family = replace(first_family, family_id="target_label:paired-secondary")
    domain = replace(reference.domains[0], families=(first_family, second_family))
    multifamily = replace(reference, domains=(domain,))

    serial = mdstats.build_target_coverage_feasibility_report(
        multifamily, role, query_workers=1, query_block_size=3, family_workers=1
    )
    parallel = mdstats.build_target_coverage_feasibility_report(
        multifamily, role, query_workers=2, query_block_size=7, family_workers=2
    )
    assert parallel.to_dict() == serial.to_dict()
    assert parallel.content_digest == serial.content_digest

def test_feas1_public_api_is_exported() -> None:
    for name in (
        "TargetCoverageFeasibilityPolicy",
        "TargetCoverageFeasibilityReport",
        "build_target_coverage_feasibility_report",
        "validate_target_coverage_feasibility_authority",
    ):
        assert name in mdstats.__all__
        assert hasattr(mdstats, name)


def test_feas1_accepts_production_style_target_data2b_reference(tmp_path) -> None:
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    report = mdstats.build_target_coverage_feasibility_report(
        reference,
        freeze,
        query_workers=1,
        query_block_size=8,
    )
    assert report.states[0] == "self_consistent"
    assert report.terminal_state in {
        "optimization_required",
        "cross_support_fragile",
        "provably_capacity_infeasible",
    }
    for domain in report.domains:
        assert domain.k_min_lower_bound >= domain.correlation_interval_count
        assert domain.k_min_lower_bound >= domain.coverage_cardinality_lower_bound
        assert all(item.neighborhood_edge_count >= item.witness_count for item in domain.family_reports)


def test_feas1_block_parallelism_is_bit_exact_and_reports_progress() -> None:
    reference, role = _reference_and_role(split_units=True)
    baseline = mdstats.build_target_coverage_feasibility_report(
        reference,
        role,
        query_workers=1,
        query_block_size=2,
        block_workers=1,
        progress_interval_seconds=0.01,
    )
    messages: list[str] = []
    parallel = mdstats.build_target_coverage_feasibility_report(
        reference,
        role,
        query_workers=1,
        query_block_size=2,
        block_workers=3,
        progress_interval_seconds=0.01,
        progress_callback=messages.append,
    )
    assert parallel.to_dict() == baseline.to_dict()
    assert parallel.content_digest == baseline.content_digest
    assert any("global-workers=3" in message for message in messages)
    assert any("tree-workers/task=1" in message for message in messages)
    assert any("profiles=1" in message and "blocks=" in message and "progress=" in message for message in messages)
    assert any("eta=" in message and "rate=" in message for message in messages)
    assert any("status=profile-complete" in message and "profile=1/1" in message for message in messages)


def test_feas1_cli_parallelism_uses_block_workers_when_budget_allows() -> None:
    from mdstats.training_data import campaign_cli

    reference, _ = _reference_and_role(split_units=True)
    tree_workers, block_workers, resources = campaign_cli._target_coverage_feasibility_parallelism(
        {
            "performance": {
                "cpu_fraction": 0.90,
                "ram_fraction": 0.80,
                "gpu_memory_fraction": 0.90,
                "target_coverage_workers": 0,
                "target_coverage_feasibility_block_workers": 0,
                "target_coverage_feasibility_family_workers": 0,
            }
        },
        reference,
        query_block_size=2,
    )
    assert block_workers * tree_workers <= resources.cpu_threads_budget
    if resources.cpu_threads_budget >= 2:
        assert tree_workers == 1
        assert block_workers == resources.cpu_threads_budget


def test_feas1_global_progress_counts_all_profiles_not_only_current_family() -> None:
    reference, role = _reference_and_role(split_units=True)
    first_family = reference.domains[0].families[0]
    families = tuple(
        replace(first_family, family_id=f"target_label:profile-{index:02d}")
        for index in range(6)
    )
    reference = replace(
        reference,
        domains=(replace(reference.domains[0], families=families),),
    )
    messages: list[str] = []
    parallel = mdstats.build_target_coverage_feasibility_report(
        reference,
        role,
        query_workers=8,
        query_block_size=2,
        block_workers=4,
        progress_interval_seconds=0.01,
        progress_callback=messages.append,
    )
    serial = mdstats.build_target_coverage_feasibility_report(
        reference,
        role,
        query_workers=1,
        query_block_size=2,
        block_workers=1,
    )
    assert parallel.to_dict() == serial.to_dict()
    assert any("status=start" in message and "profiles=6" in message for message in messages)
    completion = [message for message in messages if message.startswith("status=profile-complete;")]
    assert len(completion) == 6
    assert any("profile=6/6" in message for message in completion)
    assert all("manifest=" in message for message in completion)


def test_feas1_global_worker_setting_and_legacy_aliases_must_agree() -> None:
    from mdstats.training_data import campaign_cli

    reference, _ = _reference_and_role(split_units=True)
    tree_workers, global_workers, resources = campaign_cli._target_coverage_feasibility_parallelism(
        {
            "performance": {
                "cpu_fraction": 0.90,
                "ram_fraction": 0.80,
                "gpu_memory_fraction": 0.90,
                "target_coverage_workers": 8,
                "target_coverage_feasibility_global_workers": 3,
                "target_coverage_feasibility_block_workers": 3,
                "target_coverage_feasibility_family_workers": 0,
            }
        },
        reference,
        query_block_size=2,
    )
    assert global_workers == min(3, resources.cpu_threads_budget, resources.cpu_threads_available)
    if global_workers > 1:
        assert tree_workers == 1

    with pytest.raises(campaign_cli.CampaignCliError, match="worker controls disagree"):
        campaign_cli._target_coverage_feasibility_parallelism(
            {
                "performance": {
                    "cpu_fraction": 0.90,
                    "ram_fraction": 0.80,
                    "gpu_memory_fraction": 0.90,
                    "target_coverage_feasibility_global_workers": 4,
                    "target_coverage_feasibility_block_workers": 3,
                }
            },
            reference,
            query_block_size=2,
        )


def test_feas1_file_backed_neighbor_outputs_can_exceed_stage_ram_budget() -> None:
    reference, role = _reference_and_role(split_units=True)
    first = reference.domains[0].families[0]
    families = (first,) + tuple(
        replace(
            first,
            family_id=f"target_label:aggregate-{index:03d}",
            required=False,
        )
        for index in range(1, 266)
    )
    domain = replace(reference.domains[0], families=families)
    many = replace(reference, domains=(domain,))
    ram_budget = 70_000
    scope = mdstats.StageResourceScope(
        stage_name="TARGET-DATA2B-FEAS1-aggregate-output-test",
        cpu_threads_available=1,
        cpu_threads_budget=1,
        python_workers=1,
        tree_workers=1,
        blas_threads=1,
        ram_budget_bytes=ram_budget,
    )

    report, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(
        many,
        role,
        query_workers=1,
        query_block_size=16,
        block_workers=1,
        resource_scope=scope,
    )

    final_payload_bytes = sum(
        family.witness_offsets.nbytes + family.witness_candidates.nbytes
        for output_domain in neighborhoods.domains
        for family in output_domain.families
    )
    assert final_payload_bytes > ram_budget
    assert len(report.domains[0].family_reports) == 266
    assert len(neighborhoods.domains[0].families) == 266
    first_output = neighborhoods.domains[0].families[0]
    current = first_output.witness_candidates
    while isinstance(current, np.ndarray) and not isinstance(current, np.memmap):
        current = current.base
    assert isinstance(current, np.memmap)
