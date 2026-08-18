from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_coverage as tc
from tests.test_mlff_target_data2b_coverage import _Data5, _simple_reference, _uid


def _contains_memmap(array: np.ndarray) -> bool:
    current: object | None = array
    for _ in range(8):
        if isinstance(current, np.memmap):
            return True
        current = getattr(current, "base", None)
        if current is None:
            break
    return False


def _two_family_reference(size: int = 257) -> mdstats.TargetCoverageReference:
    reference = _simple_reference(np.linspace(-1.0, 2.0, size))
    first = reference.domains[0].families[0]
    second = replace(
        first,
        family_id="test:second",
        semantic_family="test_second",
        values=np.asarray(first.values) * 2.0 + 1.0,
        scales=np.asarray(first.scales) * 2.0,
        local_radii=np.asarray(first.local_radii),
    )
    domain = replace(reference.domains[0], families=(first, second))
    return replace(reference, domains=(domain,))


def test_perf_p0_family_arrays_are_canonical_native_authority() -> None:
    family = _simple_reference(np.arange(33.0)).domains[0].families[0]
    for array, dtype in (
        (family.frame_indices, "<i8"),
        (family.values, "<f8"),
        (family.weights, "<f8"),
        (family.scales, "<f8"),
        (family.local_radii, "<f8"),
    ):
        assert isinstance(array, np.ndarray)
        assert array.dtype.str == dtype
        assert array.flags.c_contiguous
        assert not array.flags.writeable
    assert set(family.array_references) == {
        "frame_indices", "values", "weights", "scales", "local_radii"
    }
    assert family.to_dict()["schema"] == mdstats.TARGET_COVERAGE_FAMILY_SCHEMA


def test_perf_p0_v1_to_v2_migration_is_numerically_exact() -> None:
    current = _two_family_reference()
    legacy_payload = current.to_legacy_v1_dict()
    legacy = mdstats.TargetCoverageReference.from_dict(legacy_payload)
    migrated = mdstats.TargetCoverageReference(
        dataset_id=legacy.dataset_id,
        source_catalog_digest=legacy.source_catalog_digest,
        frame_catalog_digest=legacy.frame_catalog_digest,
        data4_bundle_digest=legacy.data4_bundle_digest,
        data5_bundle_digest=legacy.data5_bundle_digest,
        data6_bundle_digest=legacy.data6_bundle_digest,
        target_data_role_freeze_digest=legacy.target_data_role_freeze_digest,
        foundation_target_audit_digest=legacy.foundation_target_audit_digest,
        policy=legacy.policy,
        domains=legacy.domains,
    )
    report = mdstats.compare_target_coverage_references_exact(legacy, migrated)
    assert legacy.requires_native_persistence_migration
    assert legacy.source_content_digest == legacy_payload["content_digest"]
    assert report.exact_match
    assert report.difference_paths == ()
    assert mdstats.TargetCoverageMigrationReport.from_dict(report.to_dict()) == report


def test_perf_p0_native_store_deduplicates_profiles_and_mmaps(tmp_path: Path) -> None:
    reference = _two_family_reference(2049)
    pointer = mdstats.write_target_coverage_native_record(
        reference, tmp_path / "records"
    )
    assert pointer["schema"] == mdstats.TARGET_COVERAGE_NATIVE_POINTER_SCHEMA
    manifest_path = tmp_path / pointer["relative_path"]
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["weight_profiles"]) == 1
    assert len(manifest["domains"][0]["families"]) == 2

    restored = mdstats.read_target_coverage_native_record(
        pointer, tmp_path, mmap_threshold_bytes=0
    )
    assert restored.content_digest == reference.content_digest
    assert mdstats.compare_target_coverage_references_exact(reference, restored).exact_match
    assert _contains_memmap(restored.domains[0].families[0].values)
    assert not restored.domains[0].families[0].values.flags.writeable


def test_perf_p0_native_store_fails_closed_on_array_tampering(tmp_path: Path) -> None:
    reference = _simple_reference(np.arange(129.0))
    pointer = mdstats.write_target_coverage_native_record(
        reference, tmp_path / "records"
    )
    manifest_path = tmp_path / pointer["relative_path"]
    manifest = json.loads(manifest_path.read_text())
    descriptor = manifest["domains"][0]["families"][0]["arrays"]["values"]
    array_path = manifest_path.parent / descriptor["relative_path"]
    with array_path.open("r+b") as handle:
        handle.seek(-1, 2)
        byte = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([byte[0] ^ 0x01]))
    with pytest.raises(mdstats.TargetCoverageNativeStoreError, match="Checksum mismatch"):
        mdstats.read_target_coverage_native_record(pointer, tmp_path)


def test_perf_p0_uniform_rank_path_matches_weighted_oracle_with_ties() -> None:
    rng = np.random.default_rng(20260815)
    points = rng.normal(size=(257, 5))
    points[1] = points[0]
    points[3:7] = points[2]
    weights = np.full(points.shape[0], 1.0 / points.shape[0], dtype=np.float64)
    for beta in (1.0 / 128.0, 0.05, 0.5):
        fast = tc._local_reference_radii(
            points,
            weights,
            beta=beta,
            leave_one_out=True,
            uniform_fast_path=True,
            query_workers=1,
        )
        oracle = tc._local_reference_radii(
            points,
            weights,
            beta=beta,
            leave_one_out=True,
            uniform_fast_path=False,
            query_workers=1,
        )
        assert np.array_equal(fast, oracle)


def test_perf_p0_weight_cache_and_uncached_family_are_identical() -> None:
    frame_uids = tuple(_uid(index + 1) for index in range(257))
    domain_index = {uid: index for index, uid in enumerate(frame_uids)}
    units = {uid: f"unit-{index // 3}" for index, uid in enumerate(frame_uids)}
    values = np.column_stack(
        (
            np.linspace(-2.0, 3.0, len(frame_uids)),
            np.cos(np.linspace(0.0, 9.0, len(frame_uids))),
        )
    )
    policy = mdstats.TargetCoveragePolicy()
    uncached = tc._build_family(
        family_id="cache:test",
        family_kind="target_label",
        semantic_family="cache_test",
        feature_names=("x", "y"),
        frame_uids=frame_uids,
        values=values,
        domain_frame_index=domain_index,
        data5_bundle=_Data5(units),
        policy=policy,
        source_evidence_digest="a" * 64,
        extent=True,
    )
    context = tc._TargetCoverageExecutionContext(
        label_domain_id="target",
        correlation_unit_by_uid=units,
        weight_cache=tc._TargetCoverageBuildCache(),
        radius_block_size=37,
        uniform_fast_path=True,
    )
    cached = tc._build_family(
        family_id="cache:test",
        family_kind="target_label",
        semantic_family="cache_test",
        feature_names=("x", "y"),
        frame_uids=frame_uids,
        values=values,
        domain_frame_index=domain_index,
        data5_bundle=_Data5(units),
        policy=policy,
        source_evidence_digest="a" * 64,
        extent=True,
        execution_context=context,
    )
    assert uncached is not None and cached is not None
    assert cached.content_digest == uncached.content_digest
    assert len(context.weight_cache.profiles) == 1


def test_perf_p0_one_sort_statistics_preserve_legacy_quantiles() -> None:
    rng = np.random.default_rng(7)
    matrix = rng.normal(size=(1025, 4))
    matrix[::17, 0] = 0.0
    raw_weights = rng.random(matrix.shape[0])
    weights = raw_weights / np.sum(raw_weights)
    statistics = tc._weighted_column_statistics(
        matrix, weights, minimum=1.0e-12, extent_alpha=0.01
    )
    expected_scales = []
    expected_lower = []
    expected_upper = []
    for column in range(matrix.shape[1]):
        values = matrix[:, column]
        q25 = tc._weighted_quantile(values, weights, 0.25)
        q75 = tc._weighted_quantile(values, weights, 0.75)
        scale = q75 - q25
        if scale <= 1.0e-12:
            scale = (
                tc._weighted_quantile(values, weights, 0.99)
                - tc._weighted_quantile(values, weights, 0.01)
            )
        if scale <= 1.0e-12:
            scale = max(float(np.std(values)), 1.0)
        expected_scales.append(max(scale, 1.0e-12))
        expected_lower.append(tc._weighted_quantile(values, weights, 0.01))
        expected_upper.append(tc._weighted_quantile(values, weights, 0.99))
    assert np.array_equal(statistics.scales, np.asarray(expected_scales))
    assert np.array_equal(statistics.lower_extents, np.asarray(expected_lower))
    assert np.array_equal(statistics.upper_extents, np.asarray(expected_upper))


def test_perf_p0_dense_backend_is_qualified_under_declared_tolerance() -> None:
    rng = np.random.default_rng(41)
    points = rng.normal(size=(83, 7))
    points[4] = points[3]
    weights = rng.random(points.shape[0])
    weights /= np.sum(weights)
    tree = tc._local_reference_radii(
        points,
        weights,
        beta=0.075,
        leave_one_out=True,
        uniform_fast_path=False,
        query_workers=1,
    )
    dense = tc._local_reference_radii_dense_exact(
        points,
        weights,
        beta=0.075,
        leave_one_out=True,
        block_size=11,
    )
    assert np.allclose(tree, dense, rtol=1.0e-13, atol=1.0e-15)


def test_perf_p0_execution_settings_do_not_enter_scientific_digest() -> None:
    frame_uids = tuple(_uid(index + 1) for index in range(129))
    domain_index = {uid: index for index, uid in enumerate(frame_uids)}
    units = {uid: f"unit-{index}" for index, uid in enumerate(frame_uids)}
    values = np.linspace(-3.0, 4.0, len(frame_uids))[:, None]
    common = dict(
        family_id="execution:test",
        family_kind="target_label",
        semantic_family="execution_test",
        feature_names=("x",),
        frame_uids=frame_uids,
        values=values,
        domain_frame_index=domain_index,
        data5_bundle=_Data5(units),
        policy=mdstats.TargetCoveragePolicy(),
        source_evidence_digest="f" * 64,
        extent=True,
    )
    a = tc._build_family(**common, query_workers=1, radius_block_size=17)
    b = tc._build_family(**common, query_workers=2, radius_block_size=61)
    assert a is not None and b is not None
    assert a.content_digest == b.content_digest
