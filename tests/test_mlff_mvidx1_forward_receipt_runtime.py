from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data import mvidx1_forward_receipt_runtime as runtime
from mdstats.training_data import target_coverage_sparse_index_store as store
from tests._mlff_multiview_legacy_fixtures import _index

forward_types = importlib.import_module(
    "mdstats.training_data.target_coverage_sparse_forward_view"
)


def _native_fixture(tmp_path: Path):
    _, index = _index()
    state_root = tmp_path / "state"
    pointer = store.write_target_coverage_sparse_index_native_record(
        index,
        state_root / "native",
    )
    return index, pointer, state_root


def _assert_same_forward_view(left, right) -> None:
    assert left.dataset_id == right.dataset_id
    assert left.mvidx1_content_digest == right.mvidx1_content_digest
    assert left.target_coverage_reference_digest == right.target_coverage_reference_digest
    assert left.target_data_role_freeze_digest == right.target_data_role_freeze_digest
    assert left.target_coverage_feasibility_digest == right.target_coverage_feasibility_digest
    assert tuple(item.label_domain_id for item in left.domains) == tuple(
        item.label_domain_id for item in right.domains
    )
    for left_domain, right_domain in zip(left.domains, right.domains, strict=True):
        assert left_domain.mvidx1_domain_digest == right_domain.mvidx1_domain_digest
        assert left_domain.candidate_count == right_domain.candidate_count
        assert left_domain.obligations == right_domain.obligations
        assert left_domain.correlation_unit_ids == right_domain.correlation_unit_ids
        assert np.array_equal(
            left_domain.candidate_obligation_offsets,
            right_domain.candidate_obligation_offsets,
        )
        assert np.array_equal(
            left_domain.candidate_obligations,
            right_domain.candidate_obligations,
        )
        assert np.array_equal(
            left_domain.candidate_correlation_unit_codes,
            right_domain.candidate_correlation_unit_codes,
        )
        assert tuple(item.family_id for item in left_domain.families) == tuple(
            item.family_id for item in right_domain.families
        )
        for left_family, right_family in zip(
            left_domain.families,
            right_domain.families,
            strict=True,
        ):
            assert left_family.family_digest == right_family.family_digest
            assert left_family.mvidx1_family_digest == right_family.mvidx1_family_digest
            assert left_family.candidate_count == right_family.candidate_count
            assert left_family.witness_count == right_family.witness_count
            assert left_family.array_references == right_family.array_references
            assert np.array_equal(left_family.candidate_offsets, right_family.candidate_offsets)
            assert np.array_equal(left_family.candidate_witnesses, right_family.candidate_witnesses)


def test_forward_receipt_miss_delegates_to_canonical_reader(monkeypatch, tmp_path: Path) -> None:
    _, pointer, state_root = _native_fixture(tmp_path)
    sentinel = object()
    calls = []

    monkeypatch.setattr(store, "read_validation_receipt", lambda *args: None)

    def canonical(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(
        store,
        "read_target_coverage_sparse_index_forward_view_native_record",
        canonical,
    )
    observed = runtime.read_target_coverage_sparse_index_forward_view_native_record_receipt_aware(
        pointer,
        state_root,
        mmap_threshold_bytes=0,
    )
    assert observed is sentinel
    assert len(calls) == 1
    assert calls[0][0] == (pointer, state_root)
    assert calls[0][1] == {"mmap_threshold_bytes": 0}


def test_forward_receipt_hit_is_exact_and_skips_family_value_rescans(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _, pointer, state_root = _native_fixture(tmp_path)
    expected = store.read_target_coverage_sparse_index_forward_view_native_record(
        pointer,
        state_root,
        mmap_threshold_bytes=0,
    )

    monkeypatch.setattr(
        store,
        "read_validation_receipt",
        lambda namespace, identity: pointer["content_digest"],
    )
    original_read_npy = store._read_npy
    read_calls = []

    def observed_read_npy(*args, **kwargs):
        read_calls.append(
            (
                kwargs.get("label"),
                kwargs.get("validate_array_reference", True),
            )
        )
        return original_read_npy(*args, **kwargs)

    monkeypatch.setattr(store, "_read_npy", observed_read_npy)
    original_sorted_rows = forward_types._validate_sorted_unique_rows
    sorted_row_names = []

    def observed_sorted_rows(offsets, values, *, name):
        sorted_row_names.append(name)
        return original_sorted_rows(offsets, values, name=name)

    monkeypatch.setattr(forward_types, "_validate_sorted_unique_rows", observed_sorted_rows)

    observed = runtime.read_target_coverage_sparse_index_forward_view_native_record_receipt_aware(
        pointer,
        state_root,
        mmap_threshold_bytes=0,
    )
    _assert_same_forward_view(observed, expected)

    family_calls = [
        (label, validate)
        for label, validate in read_calls
        if label in {"candidate_offsets", "candidate_witnesses"}
    ]
    assert family_calls
    assert all(validate is False for _, validate in family_calls)
    assert "forward candidate-to-witness" not in sorted_row_names


def test_forward_receipt_hit_fails_if_sidecar_identity_changes_during_open(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _, pointer, state_root = _native_fixture(tmp_path)
    monkeypatch.setattr(
        store,
        "read_validation_receipt",
        lambda namespace, identity: pointer["content_digest"],
    )
    original_restore_identity = store._restore_identity
    calls = 0

    def changing_identity(data_root, manifest):
        nonlocal calls
        calls += 1
        identity, logical_bytes = original_restore_identity(data_root, manifest)
        if calls == 1:
            return identity, logical_bytes
        return "f" * 64, logical_bytes

    monkeypatch.setattr(store, "_restore_identity", changing_identity)
    with pytest.raises(
        store.TargetCoverageSparseIndexNativeStoreError,
        match="sidecar identity changed during forward restore",
    ):
        runtime.read_target_coverage_sparse_index_forward_view_native_record_receipt_aware(
            pointer,
            state_root,
            mmap_threshold_bytes=0,
        )
    assert calls == 2


def test_forward_receipt_runtime_installs_only_shared_forward_reader() -> None:
    owner = SimpleNamespace(
        read_target_coverage_sparse_index_forward_view_native_record=object()
    )
    runtime.install_forward_receipt_runtime(owner)
    assert (
        owner.read_target_coverage_sparse_index_forward_view_native_record
        is runtime.read_target_coverage_sparse_index_forward_view_native_record_receipt_aware
    )
