from __future__ import annotations

import numpy as np
import pytest

import mdstats
from mdstats.analysis.local_structure import (
    _LocalStructureScratch,
    _compute_local_structure_features_arrays,
    _local_structure_topology_workspace,
)
from mdstats.training_data.resources import (
    GpuResourceSnapshot,
    StageResourceScope,
    SystemResourceSnapshot,
    build_stage_resource_scope,
    stage_resource_scope,
)
from tests.test_local_structure import _collection
from tests.test_mlff_foundation_audit1 import _build_audit


def _resources(cpu: int = 8) -> SystemResourceSnapshot:
    return SystemResourceSnapshot(
        cpu_threads_available=cpu,
        cpu_fraction=1.0,
        cpu_threads_budget=cpu,
        ram_available_bytes=4 * 1024**3,
        ram_fraction=1.0,
        ram_budget_bytes=4 * 1024**3,
        gpu_memory_fraction=1.0,
        gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "test"),
    )


def test_perf_p3_direct_local_structure_kernel_is_bitwise_reference_equivalent() -> None:
    rng = np.random.default_rng(20260815)
    cell = np.asarray(
        [[17.363, 0.0, 0.0], [8.6815, 15.0368, 0.0], [8.6815, 5.0123, 14.1768]],
        dtype=np.float64,
    )
    numbers = tuple(np.resize(np.asarray([8, 13, 14, 11], dtype=int), 48))
    fractional = rng.random((48, 3))
    collection = _collection(
        fractional @ cell,
        numbers=numbers,
        cell=cell,
        pbc=(True, True, True),
    )
    policy = mdstats.LocalStructureFeaturePolicy(maximum_dense_pair_work=10_000_000)
    reference = mdstats.compute_local_structure_features(
        collection, frame_index=0, policy=policy
    )
    topology = _local_structure_topology_workspace(
        collection.atomic_numbers, policy=policy
    )
    direct = _compute_local_structure_features_arrays(
        atomic_numbers=collection.atomic_numbers,
        fractional_positions=collection.fractional_positions[0],
        cell=collection.cells[0],
        pbc=collection.pbc,
        origin=collection.origins[0],
        frame_index=0,
        policy=policy,
        topology_workspace=topology,
        scratch=_LocalStructureScratch(),
    )
    assert direct.feature_names == reference.feature_names
    assert direct.warning_codes == reference.warning_codes
    assert direct.metadata == reference.metadata
    assert np.array_equal(direct.atom_indices, reference.atom_indices)
    assert np.array_equal(direct.atomic_numbers, reference.atomic_numbers)
    assert np.array_equal(direct.values, reference.values)
    assert np.array_equal(direct.missing_mask, reference.missing_mask)


def test_perf_p3_foundation_audit_mmap_and_memory_paths_are_identical(tmp_path) -> None:
    sources, frames, frame_data, data5, data6, freeze, sweep, memory, _ = _build_audit(
        tmp_path / "memory"
    )
    mapped = mdstats.build_foundation_target_audit(
        sources,
        frames,
        frame_data,
        data5,
        data6,
        freeze,
        sweep,
        temporary_memory_threshold_bytes=1,
        temporary_directory=str(tmp_path),
    )
    assert mapped.content_digest == memory.content_digest
    assert mapped.to_dict() == memory.to_dict()
    assert not tuple(tmp_path.glob("mdstats-foundation-audit-*"))


def test_perf_p3_stage_resource_scope_rejects_nested_oversubscription() -> None:
    resources = _resources(8)
    scope = build_stage_resource_scope(
        resources,
        stage_name="DATA6-structural",
        structural_workers=8,
        blas_threads=1,
    )
    assert scope.estimated_nested_cpu_threads == 8
    assert "cpu=8/8" in scope.summary()
    with stage_resource_scope(scope) as active:
        assert active is scope

    with pytest.raises(ValueError, match="nested CPU threads"):
        StageResourceScope(
            stage_name="oversubscribed",
            cpu_threads_available=8,
            cpu_threads_budget=8,
            python_workers=2,
            structural_workers=4,
            blas_threads=2,
        )


def test_perf_p3_tree_scope_fits_one_declared_stage_budget() -> None:
    scope = build_stage_resource_scope(
        _resources(8),
        stage_name="TARGET-DATA2B",
        tree_workers=8,
        blas_threads=1,
    )
    assert scope.estimated_nested_cpu_threads == 8
    assert scope.tree_workers == 8
    assert scope.blas_threads == 1
