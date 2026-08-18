from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data.campaign_cli import CampaignStore
from mdstats.training_data import target_coverage_sparse_index as mvidx
from tests.test_mlff_target_data2b_feas1 import _reference_and_role


def _index(*, split_units: bool = True, workers: int = 1, block: int = 3):
    reference, role = _reference_and_role(split_units=split_units)
    feas = mdstats.build_target_coverage_feasibility_report(reference, role)
    index = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feas,
        query_workers=workers,
        query_block_size=block,
    )
    return reference, role, feas, index


def test_mvidx1_is_deterministic_bidirectional_and_geometry_exact() -> None:
    reference, role, feas, first = _index(workers=1, block=3)
    _, _, _, second = _index(workers=2, block=7)
    assert first.content_digest == second.content_digest
    domain = first.domain("target")
    family = domain.family("target_label:paired")
    assert family.edge_count == 32
    assert family.witness_count == family.candidate_count == 16
    for witness in range(family.witness_count):
        candidates = family.witness_candidate_indices(witness)
        assert len(candidates) == 2
        for candidate in candidates:
            assert witness in family.candidate_witness_indices(int(candidate))
    mdstats.validate_target_coverage_sparse_index_authority(
        first,
        target_coverage_reference=reference,
        target_data_role_freeze=role,
        target_coverage_feasibility=feas,
        verify_geometry=True,
        query_workers=2,
        query_block_size=5,
    )


def test_mvidx1_covered_mass_and_marginal_gain_match_target_data2b_authority() -> None:
    reference, _, _, index = _index()
    domain = reference.domain("target")
    family_ref = domain.family("target_label:paired")
    family_index = index.domain("target").family("target_label:paired")

    selected = [0, 4, 8]
    selected_uids = [domain.frame_uids[i] for i in selected]
    report = mdstats.score_target_subset_coverage(reference, "target", selected_uids)
    authoritative = next(item for item in report.family_reports if item.family_id == family_ref.family_id)
    indexed_mass = mdstats.indexed_family_covered_mass(
        family_index, family_ref.weights, selected
    )
    assert indexed_mass == pytest.approx(authoritative.covered_reference_mass, abs=1.0e-15)

    covered = mdstats.indexed_family_covered_mask(family_index, selected)
    candidate = 12
    gain = mdstats.indexed_family_marginal_gain(
        family_index, family_ref.weights, covered, candidate
    )
    expanded = selected + [candidate]
    before = indexed_mass
    after = mdstats.indexed_family_covered_mass(family_index, family_ref.weights, expanded)
    assert gain == pytest.approx(after - before, abs=1.0e-15)


def test_mvidx1_hard_obligations_cover_extents_strata_and_intervals() -> None:
    _, role, _, index = _index()
    domain = index.domain("target")
    kinds = [item.obligation_kind for item in domain.obligations]
    assert kinds.count("extent_lower") == 1
    assert kinds.count("extent_upper") == 1
    assert kinds.count("stratum") == 1
    assert kinds.count("correlation_interval") == len(role.domain("target").development_intervals)
    assert len(domain.correlation_unit_ids) == len(role.domain("target").development_intervals)
    assert set(np.unique(domain.candidate_correlation_unit_codes)) == set(range(len(domain.correlation_unit_ids)))

    for obligation_index, obligation in enumerate(domain.obligations):
        candidates = domain.obligation_candidate_indices(obligation_index)
        assert candidates.size >= obligation.minimum_selected_frames
        for candidate in candidates:
            assert obligation_index in domain.candidate_obligation_indices(int(candidate))

    selected = list(range(domain.candidate_count))
    counts = mdstats.indexed_obligation_selected_counts(domain, selected)
    assert np.all(counts >= np.asarray([item.minimum_selected_frames for item in domain.obligations]))


def test_mvidx1_inline_round_trip_and_native_campaign_store(tmp_path: Path) -> None:
    reference, role, feas, index = _index()
    inline = mdstats.TargetCoverageSparseIndex.from_dict(index.to_dict())
    assert inline.content_digest == index.content_digest

    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        store.put_record("target_coverage_sparse_index", index)
        restored = store.get_record("target_coverage_sparse_index", mdstats.TargetCoverageSparseIndex)
        assert restored.content_digest == index.content_digest
        mdstats.validate_target_coverage_sparse_index_authority(
            restored,
            target_coverage_reference=reference,
            target_data_role_freeze=role,
            target_coverage_feasibility=feas,
        )
        refs = store.storage_references()
        assert any("target-coverage-sparse-index-" in str(path) for path in refs)
    finally:
        store.close()


def test_mvidx1_native_store_detects_tampering(tmp_path: Path) -> None:
    _, _, _, index = _index()
    records = tmp_path / "records"
    pointer = mdstats.write_target_coverage_sparse_index_native_record(index, records)
    manifest = tmp_path / pointer["relative_path"]
    payload = json.loads(manifest.read_text())
    family_array = payload["domains"][0]["families"][0]["arrays"]["witness_candidates"]
    array_path = manifest.parent / family_array["relative_path"]
    with array_path.open("r+b") as handle:
        handle.seek(-1, 2)
        byte = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([byte[0] ^ 0x01]))
    with pytest.raises(mdstats.TargetCoverageSparseIndexNativeStoreError, match="Checksum mismatch"):
        mdstats.read_target_coverage_sparse_index_native_record(pointer, tmp_path)


def test_mvidx1_public_api_is_exported() -> None:
    for name in (
        "TargetCoverageSparseIndexPolicy",
        "TargetCoverageSparseFamilyIndex",
        "TargetCoverageHardObligation",
        "TargetCoverageSparseDomainIndex",
        "TargetCoverageSparseIndex",
        "build_target_coverage_sparse_index",
        "validate_target_coverage_sparse_index_authority",
        "indexed_family_covered_mass",
        "indexed_family_marginal_gain",
        "write_target_coverage_sparse_index_native_record",
        "read_target_coverage_sparse_index_native_record",
    ):
        assert name in mdstats.__all__
        assert hasattr(mdstats, name)


def test_mvidx1_reports_block_level_progress() -> None:
    reference, role = _reference_and_role(split_units=True)
    feasibility = mdstats.build_target_coverage_feasibility_report(reference, role)
    messages: list[str] = []
    mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        query_workers=1,
        query_block_size=2,
        progress_interval_seconds=0.01,
        progress_callback=messages.append,
    )
    assert any("families=" in message and "blocks=" in message and "progress=" in message for message in messages)
    assert any("rate=" in message and "eta=" in message and "edges=" in message for message in messages)


def test_mvidx1_accepts_production_style_target_data2b_reference(tmp_path: Path) -> None:
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    feas = mdstats.build_target_coverage_feasibility_report(reference, freeze, query_block_size=8)
    index = mdstats.build_target_coverage_sparse_index(
        reference,
        freeze,
        feas,
        query_workers=1,
        query_block_size=8,
    )
    mdstats.validate_target_coverage_sparse_index_authority(
        index,
        target_coverage_reference=reference,
        target_data_role_freeze=freeze,
        target_coverage_feasibility=feas,
        verify_geometry=True,
        query_workers=1,
        query_block_size=8,
    )
    for domain in index.domains:
        required_ids = {item.family_id for item in reference.domain(domain.label_domain_id).families if item.required}
        assert {item.family_id for item in domain.families} == required_ids
        assert all(item.edge_count >= item.witness_count for item in domain.families)
        assert len(domain.correlation_unit_ids) >= 1


def test_mvidx1_out_of_core_inverse_is_byte_exact_across_many_chunks(tmp_path: Path) -> None:
    rng = np.random.default_rng(20260817)
    row_count = 500
    column_count = 200
    rows = [
        np.sort(rng.choice(column_count, size=int(rng.integers(0, 50)), replace=False)).astype("<u4")
        for _ in range(row_count)
    ]
    offsets = np.empty(row_count + 1, dtype="<u8")
    offsets[0] = 0
    np.cumsum(np.asarray([len(row) for row in rows], dtype=np.uint64), out=offsets[1:])
    columns = np.concatenate(rows).astype("<u4")

    expected_offsets, expected_rows = mvidx._csr_inverse(
        offsets, columns, row_count=row_count, column_count=column_count
    )
    actual_offsets, actual_rows = mvidx._csr_inverse_out_of_core(
        offsets,
        columns,
        row_count=row_count,
        column_count=column_count,
        output_path=tmp_path / "candidate-witnesses.npy",
        # Deliberately tiny scratch forces many source-row chunks.
        chunk_scratch_bytes=4096,
    )
    assert np.array_equal(actual_offsets, expected_offsets)
    assert np.array_equal(actual_rows, expected_rows)
    assert isinstance(actual_rows, np.memmap)


def test_mvidx1_out_of_core_family_path_preserves_complete_index_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference, role = _reference_and_role(split_units=True)
    feasibility, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(
        reference, role, query_workers=1, query_block_size=3, block_workers=2
    )
    expected = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        query_workers=1,
        global_workers=2,
    )
    monkeypatch.setattr(mvidx, "_MVIDX_OUT_OF_CORE_MIN_OUTPUT_BYTES", 1)
    actual = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        query_workers=1,
        global_workers=2,
        out_of_core_directory=tmp_path / "ooc",
    )
    assert actual.content_digest == expected.content_digest
    for expected_domain, actual_domain in zip(expected.domains, actual.domains, strict=True):
        for expected_family, actual_family in zip(expected_domain.families, actual_domain.families, strict=True):
            assert np.array_equal(actual_family.candidate_offsets, expected_family.candidate_offsets)
            assert np.array_equal(actual_family.candidate_witnesses, expected_family.candidate_witnesses)


def test_mvidx1_native_store_hardlinks_whole_out_of_core_npy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mdstats.training_data import target_coverage_sparse_index_store as native_store

    reference, role = _reference_and_role(split_units=True)
    feasibility, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(
        reference, role, query_workers=1, query_block_size=3, block_workers=2
    )
    monkeypatch.setattr(mvidx, "_MVIDX_OUT_OF_CORE_MIN_OUTPUT_BYTES", 1)
    build_root = tmp_path / "build"
    index = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        query_workers=1,
        global_workers=1,
        out_of_core_directory=build_root,
    )
    family = index.domains[0].families[0]
    source = native_store._whole_npy_memmap_source(family.candidate_witnesses)
    assert source is not None and source.is_file()

    records = tmp_path / "records"
    pointer = mdstats.write_target_coverage_sparse_index_native_record(index, records)
    manifest = tmp_path / pointer["relative_path"]
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    descriptor = payload["domains"][0]["families"][0]["arrays"]["candidate_witnesses"]
    durable = manifest.parent / descriptor["relative_path"]
    assert source.samefile(durable)

    restored = mdstats.read_target_coverage_sparse_index_native_record(pointer, tmp_path)
    assert restored.content_digest == index.content_digest


def test_mvidx1_out_of_core_queue_respects_explicit_small_ram_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mdstats.training_data.resources import StageResourceScope

    reference, role = _reference_and_role(split_units=True)
    feasibility, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(
        reference, role, query_workers=1, query_block_size=3, block_workers=2
    )
    expected = mdstats.build_target_coverage_sparse_index(
        reference, role, feasibility, exact_neighborhood_store=neighborhoods
    )
    monkeypatch.setattr(mvidx, "_MVIDX_OUT_OF_CORE_MIN_OUTPUT_BYTES", 1)
    scope = StageResourceScope(
        stage_name="mvidx-ooc-test",
        cpu_threads_available=2,
        cpu_threads_budget=2,
        python_workers=2,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        ram_budget_bytes=32 * 1024 * 1024,
    )
    actual = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        global_workers=2,
        resource_scope=scope,
        out_of_core_directory=tmp_path / "ooc-budgeted",
    )
    assert actual.content_digest == expected.content_digest


def test_mvidx1_bounded_producer_refills_ready_queue_without_queue_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MVIDX must stream >queue-capacity family work instead of eager-submitting it."""
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path / "inputs")
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    feasibility, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(
        reference, freeze, query_workers=1, query_block_size=8, block_workers=2
    )
    expected = mdstats.build_target_coverage_sparse_index(
        reference,
        freeze,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        query_workers=1,
        global_workers=2,
    )

    original_queue = mvidx.DeterministicWorkQueue

    class OneReadySlotQueue(original_queue):
        def __init__(self, scope, **kwargs):
            kwargs["max_ready_tasks"] = 1
            super().__init__(scope, **kwargs)

    monkeypatch.setattr(mvidx, "DeterministicWorkQueue", OneReadySlotQueue)
    monkeypatch.setattr(mvidx, "_MVIDX_OUT_OF_CORE_MIN_OUTPUT_BYTES", 1)
    actual = mdstats.build_target_coverage_sparse_index(
        reference,
        freeze,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        query_workers=1,
        global_workers=2,
        out_of_core_directory=tmp_path / "ooc-refill",
    )
    assert sum(len(domain.families) for domain in actual.domains) > 1
    assert actual.content_digest == expected.content_digest
