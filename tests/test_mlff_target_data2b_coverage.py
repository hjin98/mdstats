from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_coverage as tc


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




def _build_coverage_inputs(tmp_path: Path):
    from tests.test_mlff_data9a9a_production_model_sweep import _CountingCalculator, _inputs, _provider

    sources, frames, frame_data, data4, data5, policy = _inputs(tmp_path / "inputs")
    policy = replace(policy, build_universal_structural_features=True)
    freeze = mdstats.build_target_data_role_freeze(sources, frames, data5)
    calc = _CountingCalculator()
    provider = _provider(calc)
    sweep = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, tmp_path / "sweep"
    )
    data6 = mdstats.build_data6_feature_bundle(
        sources, frames, frame_data, data4, data5,
        policy=policy, model_provider=provider, model_sweep_artifacts=sweep,
    )
    audit = mdstats.build_foundation_target_audit(
        sources, frames, frame_data, data5, data6, freeze, sweep
    )
    return sources, frames, frame_data, data4, data5, data6, freeze, audit

def _uid(index: int) -> str:
    return f"{index:064x}"


def _simple_reference(values: np.ndarray, *, units: tuple[str, ...] | None = None) -> mdstats.TargetCoverageReference:
    values = np.asarray(values, dtype=np.float64).reshape(-1, 1)
    frame_uids = tuple(_uid(i + 1) for i in range(values.shape[0]))
    mapping = {
        uid: (units[i] if units is not None else f"unit-{i}")
        for i, uid in enumerate(frame_uids)
    }
    policy = mdstats.TargetCoveragePolicy()
    family = tc._build_family(
        family_id="test:scalar",
        family_kind="target_label",
        semantic_family="test_scalar",
        feature_names=("x",),
        frame_uids=frame_uids,
        values=values,
        domain_frame_index={uid: i for i, uid in enumerate(frame_uids)},
        data5_bundle=_Data5(mapping),
        policy=policy,
        source_evidence_digest="a" * 64,
        required=True,
        extent=True,
    )
    assert family is not None
    domain = mdstats.TargetCoverageDomainReference(
        label_domain_id="target",
        frame_uids=frame_uids,
        families=(family,),
        strata=(),
        frame_domain_digest="b" * 64,
    )
    return mdstats.TargetCoverageReference(
        dataset_id="synthetic",
        source_catalog_digest="1" * 64,
        frame_catalog_digest="2" * 64,
        data4_bundle_digest="3" * 64,
        data5_bundle_digest="4" * 64,
        data6_bundle_digest="5" * 64,
        target_data_role_freeze_digest="6" * 64,
        foundation_target_audit_digest="7" * 64,
        policy=policy,
        domains=(domain,),
    )


def test_reference_mass_coverage_cannot_be_gamed_by_two_extrema() -> None:
    reference = _simple_reference(np.linspace(0.0, 1.0, 129))
    domain = reference.domain("target")
    report = mdstats.score_target_subset_coverage(
        reference,
        "target",
        (domain.frame_uids[0], domain.frame_uids[-1]),
    )
    family = report.family_reports[0]
    assert family.covered_reference_mass < 0.10
    assert not family.coverage_passed
    assert family.extent_passed
    assert not report.passed


def test_homogeneous_center_only_subset_fails_reference_extent_and_coverage() -> None:
    reference = _simple_reference(np.linspace(0.0, 1.0, 129))
    domain = reference.domain("target")
    selected = domain.frame_uids[40:89:4]
    report = mdstats.score_target_subset_coverage(reference, "target", selected)
    family = report.family_reports[0]
    assert family.covered_reference_mass < 0.95
    assert not family.extent_passed
    assert {item.split(":")[-1] for item in family.extent_failures} == {"lower", "upper"}


def test_full_reference_is_exactly_covered_and_round_trips() -> None:
    reference = _simple_reference(np.linspace(-2.0, 3.0, 41))
    domain = reference.domain("target")
    report = mdstats.score_target_subset_coverage(reference, "target", domain.frame_uids)
    assert report.passed
    assert report.family_reports[0].covered_reference_mass == pytest.approx(1.0)
    restored = mdstats.TargetCoverageReference.from_dict(reference.to_dict())
    assert restored.content_digest == reference.content_digest
    restored_report = mdstats.TargetCoverageReport.from_dict(report.to_dict())
    assert restored_report.content_digest == report.content_digest


def test_reference_weights_balance_correlation_units_not_raw_frame_counts() -> None:
    values = np.arange(100, dtype=np.float64)
    units = tuple("long" if i < 90 else "short" for i in range(100))
    reference = _simple_reference(values, units=units)
    family = reference.domain("target").families[0]
    weights = np.asarray(family.weights)
    assert np.sum(weights[:90]) == pytest.approx(0.5)
    assert np.sum(weights[90:]) == pytest.approx(0.5)
    assert weights[0] == pytest.approx(0.5 / 90.0)
    assert weights[-1] == pytest.approx(0.5 / 10.0)


def test_nested_reference_coverage_is_monotone() -> None:
    reference = _simple_reference(np.linspace(0.0, 1.0, 65))
    frames = reference.domain("target").frame_uids
    reports = (
        mdstats.score_target_subset_coverage(reference, "target", frames[::8]),
        mdstats.score_target_subset_coverage(reference, "target", frames[::4]),
        mdstats.score_target_subset_coverage(reference, "target", frames[::2]),
        mdstats.score_target_subset_coverage(reference, "target", frames),
    )
    # Above slices are not exact prefixes/nested because Python strides do not
    # guarantee set inclusion in this order; construct exact cumulative sets.
    nested = []
    selected: list[str] = []
    for batch in (frames[::8], frames[4::8], frames[2::4], frames[1::2]):
        selected.extend(uid for uid in batch if uid not in selected)
        nested.append(mdstats.score_target_subset_coverage(reference, "target", tuple(selected)))
    mdstats.assert_nested_coverage_monotonicity(nested)
    masses = [item.family_reports[0].covered_reference_mass for item in nested]
    assert masses == sorted(masses)


def test_target_data2b_builds_only_on_frozen_development_domain_and_full_selection_passes(tmp_path: Path) -> None:
    sources, frames, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)

    reference = mdstats.build_target_coverage_reference(
        data4,
        data5,
        data6,
        freeze,
        audit,
    )
    assert reference.target_data_role_freeze_digest == freeze.content_digest
    assert reference.foundation_target_audit_digest == audit.content_digest
    mdstats.validate_target_coverage_reference_authority(
        reference,
        data4_bundle=data4,
        data5_bundle=data5,
        data6_bundle=data6,
        target_data_role_freeze=freeze,
        foundation_target_audit=audit,
    )

    for frozen in freeze.domains:
        domain = reference.domain(frozen.label_domain_id)
        assert domain.frame_uids == tuple(sorted(frozen.size_development_frame_uids))
        protected = set(frozen.final_validation_frame_uids) | set(frozen.locked_test_frame_uids)
        assert protected.isdisjoint(domain.frame_uids)
        family_kinds = {item.family_kind for item in domain.families}
        assert {"structural", "target_label", "foundation_residual"} <= family_kinds
        assert any(item.family_id == "foundation_residual:global" for item in domain.families)
        report = mdstats.score_target_subset_coverage(reference, frozen.label_domain_id, domain.frame_uids)
        assert report.passed
        assert all(item.covered_reference_mass == pytest.approx(1.0) for item in report.family_reports if item.required)
        assert all(item.extent_passed for item in report.family_reports if item.required)
        assert all(item.passed for item in report.stratum_reports if item.required)


def test_target_data2b_covers_every_required_final_and_cv_training_domain(tmp_path: Path) -> None:
    from mdstats.training_data import campaign_cli

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    training_domains = campaign_cli._target_size_required_feature_fit_domains({}, data5)
    kinds = {domain.kind for domain in training_domains}
    assert kinds == {
        mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT,
        mdstats.FeatureFitDomainKind.CROSS_VALIDATION_TRAINING,
    }

    reference = mdstats.build_target_coverage_reference(
        data4,
        data5,
        data6,
        freeze,
        audit,
        training_domains=training_domains,
    )
    by_training_digest = {
        domain.training_domain_digest: domain for domain in reference.domains
    }
    assert set(by_training_digest) == {
        domain.content_digest for domain in training_domains
    }
    for training_domain in training_domains:
        coverage_domain = by_training_digest[training_domain.content_digest]
        assert coverage_domain.source_label_domain_id == training_domain.label_domain_id
        assert coverage_domain.training_domain_kind == training_domain.kind.value
        assert coverage_domain.training_domain_fold_index == training_domain.fold_index
        assert coverage_domain.frame_uids == tuple(sorted(training_domain.frame_uids))
        role_view = tc.target_coverage_role_domain_view(freeze, coverage_domain)
        assert role_view.size_development_frame_uids == coverage_domain.frame_uids

    mdstats.validate_target_coverage_reference_authority(
        reference,
        data4_bundle=data4,
        data5_bundle=data5,
        data6_bundle=data6,
        target_data_role_freeze=freeze,
        foundation_target_audit=audit,
        training_domains=training_domains,
    )
    pointer = mdstats.write_target_coverage_native_record(
        reference, tmp_path / "target-coverage-native"
    )
    restored = mdstats.read_target_coverage_native_record(pointer, tmp_path)
    assert restored.content_digest == reference.content_digest
    assert {
        (domain.training_domain_digest, domain.training_domain_kind, domain.training_domain_fold_index)
        for domain in restored.domains
    } == {
        (domain.training_domain_digest, domain.training_domain_kind, domain.training_domain_fold_index)
        for domain in reference.domains
    }


def test_target_data2b_authority_fails_closed_if_data6_changes(tmp_path: Path) -> None:
    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    stale = replace(data6, notes=data6.notes + ("changed",))
    with pytest.raises(mdstats.TrainingDataInputError, match="data6_bundle_digest changed"):
        mdstats.validate_target_coverage_reference_authority(
            reference,
            data4_bundle=data4,
            data5_bundle=data5,
            data6_bundle=stale,
            target_data_role_freeze=freeze,
            foundation_target_audit=audit,
        )


def test_target_data2b_is_bound_into_prepare_restart_and_preflight_contract() -> None:
    from mdstats.training_data import campaign_cli

    assert "target_coverage_reference" in campaign_cli._PREPARE_RECEIPT_RECORD_KEYS
    contract = campaign_cli._prepare_contract_signature()
    assert contract["target_data2b_coverage_version"] == mdstats.TARGET_COVERAGE_VERSION
    assert callable(campaign_cli._load_verified_target_coverage_reference_authority)
    assert callable(campaign_cli._ensure_target_coverage_reference)


def test_target_data2b_campaign_authority_persists_and_reuses_without_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mdstats.training_data import campaign_cli

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path / "inputs")
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite")
    store.put_record("target_data_role_freeze", freeze)

    first = campaign_cli._ensure_target_coverage_reference(
        store,
        cfg={},
        data4=data4,
        data5=data5,
        data6=data6,
        foundation_audit=audit,
    )
    assert store.has_record("target_coverage_reference")
    restored = store.get_record("target_coverage_reference", mdstats.TargetCoverageReference)
    assert restored.content_digest == first.content_digest

    def _unexpected_rebuild(*args, **kwargs):  # pragma: no cover - only invoked on failure
        raise AssertionError("current TARGET-DATA2B authority should have been reused")

    monkeypatch.setattr(mdstats, "build_target_coverage_reference", _unexpected_rebuild)
    second = campaign_cli._ensure_target_coverage_reference(
        store,
        cfg={},
        data4=data4,
        data5=data5,
        data6=data6,
        foundation_audit=audit,
    )
    assert second.content_digest == first.content_digest


def test_target_data2b_subset_report_identity_is_order_independent() -> None:
    reference = _simple_reference(np.linspace(0.0, 1.0, 17))
    frames = reference.domain("target").frame_uids
    first = mdstats.score_target_subset_coverage(reference, "target", (frames[1], frames[8], frames[15]))
    second = mdstats.score_target_subset_coverage(reference, "target", (frames[15], frames[1], frames[8]))
    assert first.content_digest == second.content_digest
    assert first.selected_frame_uids == tuple(sorted((frames[1], frames[8], frames[15])))


def test_weighted_leave_one_out_local_radii_match_bruteforce() -> None:
    values = np.asarray([[0.0], [0.2], [0.5], [1.1], [2.0]], dtype=np.float64)
    weights = np.asarray([0.10, 0.20, 0.30, 0.15, 0.25], dtype=np.float64)
    beta = 0.40
    observed = tc._local_reference_radii(values, weights, beta=beta, leave_one_out=True)
    expected = []
    for i in range(len(values)):
        rows = sorted(
            ((abs(float(values[j, 0] - values[i, 0])), j) for j in range(len(values)) if j != i),
            key=lambda item: (item[0], item[1]),
        )
        mass = 0.0
        radius = None
        for distance, j in rows:
            mass += float(weights[j] / (1.0 - weights[i]))
            if mass >= beta - 1.0e-15:
                radius = distance
                break
        assert radius is not None
        expected.append(radius)
    np.testing.assert_allclose(observed, np.asarray(expected), rtol=0.0, atol=1.0e-14)


def test_target_data2b_consumes_profile_features_and_environment_classes_through_generic_adapter(tmp_path: Path) -> None:
    from types import SimpleNamespace
    from tests.test_mlff_data6_selection_descriptors import _site_catalogs

    sources, frames, frame_data, site_policy = _site_catalogs(tmp_path)
    data4 = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        frame_data,
        raw_feature_policy=mdstats.RawFeaturePolicy.lta_default(),
        lta_profile_policy=mdstats.LtaPartitionProfilePolicy(
            ring_definitions=site_policy.ring_definitions,
            require_oxygen_framework_coordination=1,
        ),
        event_policy=mdstats.EventDetectionPolicy(pre_frames=1, post_frames=1),
        partition_role_budget=mdstats.PartitionRoleBudgetPolicy(cross_validation_folds=2),
    )
    lta = mdstats.build_lta_selection_feature_catalog(
        frames,
        frame_data,
        data4,
        policy=mdstats.LtaSelectionPolicy(materialize_atomic_environments=False),
    )
    extension = mdstats.wrap_lta_selection_features(
        lta,
        data4_bundle_digest=data4.content_digest,
    )
    frame_uids = tuple(item.frame_uid for item in lta.frame_descriptors)
    frame_index = {uid: i for i, uid in enumerate(frame_uids)}
    data5 = _Data5({uid: f"unit-{i}" for i, uid in enumerate(frame_uids)})
    data6 = SimpleNamespace(
        profile_selection_features=(extension,),
        universal_structural_features=(),
    )
    policy = mdstats.TargetCoveragePolicy(
        require_condition_support=False,
        require_structural_event_support=False,
    )

    families = tc._profile_families_for_domain(
        domain_frame_uids=frame_uids,
        domain_frame_index=frame_index,
        data5_bundle=data5,
        data6_bundle=data6,
        policy=policy,
    )
    assert families
    assert all(item.family_kind == "profile" for item in families)
    assert all(item.semantic_family.startswith("profile:lta:") for item in families)
    assert all(item.required for item in families)
    assert all(len(item.feature_names) == 1 for item in families)

    strata = tc._strata_for_domain(
        label_domain_id="target",
        domain_frame_uids=frame_uids,
        domain_frame_index=frame_index,
        data5_bundle=data5,
        data6_bundle=data6,
        policy=policy,
    )
    labels = {item.label for item in strata if item.stratum_kind == "profile_environment"}
    assert labels
    assert {label.split(":", 2)[1] for label in labels} == {"Li", "Na", "K"}


def _scalar_local_reference_radii(values, weights, *, beta, leave_one_out):
    """Pre-PERF1 scalar reference used to lock exact TARGET-DATA2B semantics."""
    import math
    from scipy.spatial import cKDTree

    points = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    n, dim = points.shape
    tree = cKDTree(points)
    radii = np.empty(n, dtype=np.float64)
    initial_k = min(n, max(8, int(math.ceil(beta * n * 1.5)) + 2))
    norm = math.sqrt(float(dim))
    for start in range(0, n, 41):
        stop = min(n, start + 41)
        pending = np.arange(start, stop, dtype=np.int64)
        k = initial_k
        while pending.size:
            distances, neighbors = tree.query(points[pending], k=k, workers=1)
            if k == 1:
                distances = distances[:, None]
                neighbors = neighbors[:, None]
            unresolved = []
            for local_row, reference_index in enumerate(pending):
                idx = np.asarray(neighbors[local_row], dtype=np.int64)
                dst = np.asarray(distances[local_row], dtype=np.float64)
                valid = np.isfinite(dst) & (idx >= 0) & (idx < n)
                if leave_one_out:
                    valid &= idx != reference_index
                    denominator = 1.0 - weights[reference_index]
                else:
                    denominator = 1.0
                idx = idx[valid]
                dst = dst[valid]
                if idx.size == 0 or denominator <= 0.0:
                    raise RuntimeError("degenerate scalar reference")
                cumulative = np.cumsum(weights[idx] / denominator)
                hit = np.flatnonzero(cumulative >= beta - 1.0e-15)
                if hit.size:
                    radii[reference_index] = float(dst[int(hit[0])] / norm)
                elif k >= n:
                    if cumulative[-1] + 1.0e-12 < beta:
                        raise RuntimeError("unreachable scalar reference")
                    radii[reference_index] = float(dst[-1] / norm)
                else:
                    unresolved.append(int(reference_index))
            if not unresolved:
                break
            pending = np.asarray(unresolved, dtype=np.int64)
            k = min(n, max(k + 1, k * 2))
    return radii


def test_target_data2b_parallel_vectorized_local_radii_are_exact() -> None:
    rng = np.random.default_rng(104729)
    values = rng.normal(size=(513, 5))
    # Include exact duplicates/ties and deliberately nonuniform reference mass.
    values[100:104] = values[7]
    unit_sizes = (301, 127, 61, 24)
    weights = np.empty(values.shape[0], dtype=np.float64)
    cursor = 0
    for size in unit_sizes:
        weights[cursor:cursor + size] = (1.0 / len(unit_sizes)) / size
        cursor += size
    weights /= np.sum(weights)
    expected = _scalar_local_reference_radii(
        values,
        weights,
        beta=1.0 / 128.0,
        leave_one_out=True,
    )
    serial = tc._local_reference_radii(
        values,
        weights,
        beta=1.0 / 128.0,
        leave_one_out=True,
        block_size=73,
        query_workers=1,
    )
    parallel = tc._local_reference_radii(
        values,
        weights,
        beta=1.0 / 128.0,
        leave_one_out=True,
        block_size=73,
        query_workers=2,
    )
    assert np.array_equal(serial, expected)
    assert np.array_equal(parallel, expected)


def test_target_data2b_reference_digest_is_worker_count_invariant(tmp_path: Path) -> None:
    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    serial = mdstats.build_target_coverage_reference(
        data4, data5, data6, freeze, audit, query_workers=1
    )
    parallel = mdstats.build_target_coverage_reference(
        data4, data5, data6, freeze, audit, query_workers=2
    )
    assert parallel.content_digest == serial.content_digest
    assert parallel.to_dict() == serial.to_dict()
