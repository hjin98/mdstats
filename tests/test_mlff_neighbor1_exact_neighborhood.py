from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_coverage_exact_neighborhood as neigh
from mdstats.training_data.campaign_cli import CampaignStore
from tests.test_mlff_target_data2b_feas1 import _reference_and_role


def _artifacts(*, workers: int = 1, block: int = 3):
    reference, role = _reference_and_role(split_units=True)
    feasibility, store = mdstats.build_target_coverage_feasibility_artifacts(
        reference,
        role,
        query_workers=1,
        query_block_size=block,
        block_workers=workers,
    )
    return reference, role, feasibility, store


def _assert_same_store(left, right) -> None:
    assert left.content_digest == right.content_digest
    assert left.to_dict() == right.to_dict()
    for left_domain, right_domain in zip(left.domains, right.domains, strict=True):
        for left_family, right_family in zip(left_domain.families, right_domain.families, strict=True):
            assert np.array_equal(left_family.witness_offsets, right_family.witness_offsets)
            assert np.array_equal(left_family.witness_candidates, right_family.witness_candidates)


def test_neighbor1_store_is_execution_knob_invariant_and_feas1_stays_exact() -> None:
    reference, role = _reference_and_role(split_units=True)
    baseline = mdstats.build_target_coverage_feasibility_report(
        reference, role, query_workers=1, query_block_size=2, block_workers=1
    )
    report_a, store_a = mdstats.build_target_coverage_feasibility_artifacts(
        reference, role, query_workers=1, query_block_size=2, block_workers=1
    )
    report_b, store_b = mdstats.build_target_coverage_feasibility_artifacts(
        reference, role, query_workers=8, query_block_size=7, block_workers=3
    )
    assert report_a.to_dict() == baseline.to_dict() == report_b.to_dict()
    _assert_same_store(store_a, store_b)
    assert store_a.edge_count == 32
    family = store_a.domain("target").family("target_label:paired")
    assert family.identity_digest == store_b.domain("target").family("target_label:paired").identity_digest
    assert family.edge_count == 32
    assert all(len(family.witness_candidate_indices(i)) == 2 for i in range(family.witness_count))


def test_neighbor1_standalone_engine_matches_feas1_emitted_store() -> None:
    reference, role, _, emitted = _artifacts(workers=2, block=5)
    rebuilt = mdstats.build_target_coverage_exact_neighborhood_store(
        reference,
        global_workers=3,
        query_workers=7,
        query_block_size=2,
    )
    _assert_same_store(emitted, rebuilt)
    mdstats.validate_target_coverage_exact_neighborhood_store(
        rebuilt,
        target_coverage_reference=reference,
    )


def test_neighbor1_mvidx_cache_hit_performs_no_geometric_query(monkeypatch: pytest.MonkeyPatch) -> None:
    reference, role, feasibility, store = _artifacts(workers=2, block=3)
    expected = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=store,
        query_workers=1,
    )

    def forbidden(*args, **kwargs):  # pragma: no cover - only executes on regression
        raise AssertionError("MVIDX cache-hit path performed a second geometric neighborhood query")

    monkeypatch.setattr(neigh.ExactNeighborhoodEngine, "query_block", forbidden)
    actual = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=store,
        query_workers=17,
        query_block_size=1,
    )
    assert actual.to_dict() == expected.to_dict()


def test_neighbor1_mvidx_cache_rebuild_is_exact() -> None:
    reference, role, feasibility, store = _artifacts(workers=2, block=4)
    cached = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=store,
        query_workers=1,
    )
    rebuilt = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=None,
        global_workers=3,
        query_workers=8,
        query_block_size=2,
    )
    assert rebuilt.to_dict() == cached.to_dict()
    mdstats.validate_target_coverage_sparse_index_authority(
        rebuilt,
        target_coverage_reference=reference,
        target_data_role_freeze=role,
        target_coverage_feasibility=feasibility,
        verify_geometry=True,
        query_workers=3,
        query_block_size=2,
    )


def test_neighbor1_native_store_round_trip_and_campaign_references(tmp_path: Path) -> None:
    reference, _, _, store = _artifacts(workers=2, block=3)
    records = tmp_path / "records"
    pointer = mdstats.write_target_coverage_exact_neighborhood_native_record(store, records)
    restored = mdstats.read_target_coverage_exact_neighborhood_native_record(pointer, tmp_path)
    _assert_same_store(store, restored)
    mdstats.validate_target_coverage_exact_neighborhood_store(
        restored,
        target_coverage_reference=reference,
    )

    campaign = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        campaign.put_record("target_coverage_exact_neighborhoods", store)
        from_campaign = campaign.get_record(
            "target_coverage_exact_neighborhoods", mdstats.TargetCoverageExactNeighborhoodStore
        )
        _assert_same_store(store, from_campaign)
        refs = campaign.storage_references()
        assert any("target-coverage-exact-neighborhood-" in str(path) for path in refs)
    finally:
        campaign.close()


def test_neighbor1_native_store_detects_array_tampering(tmp_path: Path) -> None:
    _, _, _, store = _artifacts()
    pointer = mdstats.write_target_coverage_exact_neighborhood_native_record(store, tmp_path / "records")
    manifest = tmp_path / pointer["relative_path"]
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    descriptor = payload["domains"][0]["families"][0]["arrays"]["witness_candidates"]
    array_path = manifest.parent / descriptor["relative_path"]
    with array_path.open("r+b") as handle:
        handle.seek(-1, 2)
        byte = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([byte[0] ^ 0x01]))
    with pytest.raises(mdstats.TargetCoverageExactNeighborhoodNativeStoreError, match="Checksum mismatch"):
        mdstats.read_target_coverage_exact_neighborhood_native_record(pointer, tmp_path)


def test_neighbor1_parallel_telemetry_saturates_available_outer_lanes() -> None:
    reference, _ = _reference_and_role(split_units=True)
    # Duplicate the independent family identity so the global queue has enough
    # blocks/families to expose outer-lane scheduling in a tiny test fixture.
    domain = reference.domains[0]
    from dataclasses import replace
    families = tuple(replace(domain.families[0], family_id=f"target_label:n1-{i}") for i in range(6))
    reference = replace(reference, domains=(replace(domain, families=families),))
    store, telemetry = mdstats.build_target_coverage_exact_neighborhood_store(
        reference,
        global_workers=3,
        query_workers=9,
        query_block_size=2,
        return_telemetry=True,
    )
    assert store.edge_count == 6 * 32
    assert telemetry.allocated_workers == 3
    assert telemetry.tree_workers_per_task == 1
    assert telemetry.max_busy_workers >= 2
    assert telemetry.family_count == 6


def test_neighbor1_public_api_and_mvidx_source_use_shared_engine() -> None:
    for name in (
        "TargetCoverageExactNeighborhoodFamily",
        "TargetCoverageExactNeighborhoodDomain",
        "TargetCoverageExactNeighborhoodStore",
        "ExactNeighborhoodEngine",
        "build_target_coverage_exact_neighborhood_store",
        "validate_target_coverage_exact_neighborhood_store",
        "build_target_coverage_feasibility_artifacts",
        "write_target_coverage_exact_neighborhood_native_record",
        "read_target_coverage_exact_neighborhood_native_record",
    ):
        assert name in mdstats.__all__
        assert hasattr(mdstats, name)

    source = Path("mdstats/training_data/target_coverage_sparse_index.py").read_text(encoding="utf-8")
    assert "cKDTree" not in source
    assert "query_ball_point" not in source
    assert "build_target_coverage_exact_neighborhood_store" in source
