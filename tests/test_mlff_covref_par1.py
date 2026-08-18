from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import target_coverage as tc
from mdstats.training_data.work_queue import DeterministicWorkQueue
from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs


def _scope(workers: int) -> mdstats.StageResourceScope:
    return mdstats.StageResourceScope(
        stage_name="COVREF-PAR1-test",
        cpu_threads_available=max(3, workers),
        cpu_threads_budget=max(3, workers),
        python_workers=workers,
        tree_workers=1,
        blas_threads=1,
    )


def _nonuniform_case() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(104729)
    values = rng.normal(size=(513, 5))
    values[100:104] = values[7]
    weights = np.empty(values.shape[0], dtype=np.float64)
    cursor = 0
    for size in (301, 127, 61, 24):
        weights[cursor:cursor + size] = (1.0 / 4.0) / size
        cursor += size
    weights /= np.sum(weights, dtype=np.float64)
    return values, weights


def test_covref_par1_weighted_block_queue_is_byte_exact_and_uses_all_lanes() -> None:
    values, weights = _nonuniform_case()
    serial = tc._local_reference_radii(
        values,
        weights,
        beta=1.0 / 128.0,
        leave_one_out=True,
        block_size=73,
        query_workers=1,
    )
    with DeterministicWorkQueue(_scope(3)) as queue:
        parallel = tc._local_reference_radii(
            values,
            weights,
            beta=1.0 / 128.0,
            leave_one_out=True,
            block_size=73,
            query_workers=1,
            work_queue=queue,
            task_prefix="weighted",
        )
        snapshot = queue.snapshot()
    assert np.array_equal(parallel, serial)
    assert parallel.tobytes() == serial.tobytes()
    assert snapshot.max_busy_workers == 3
    assert snapshot.submitted_tasks >= 8
    assert snapshot.finished_tasks == snapshot.committed_tasks == snapshot.submitted_tasks


def test_covref_par1_uniform_fast_path_is_byte_exact() -> None:
    rng = np.random.default_rng(271828)
    values = rng.normal(size=(1025, 4))
    weights = np.full(values.shape[0], 1.0 / values.shape[0], dtype=np.float64)
    serial = tc._local_reference_radii(
        values,
        weights,
        beta=1.0 / 128.0,
        leave_one_out=True,
        block_size=91,
        query_workers=1,
    )
    with DeterministicWorkQueue(_scope(3)) as queue:
        parallel = tc._local_reference_radii(
            values,
            weights,
            beta=1.0 / 128.0,
            leave_one_out=True,
            block_size=91,
            query_workers=1,
            work_queue=queue,
            task_prefix="uniform",
        )
    assert np.array_equal(parallel, serial)
    assert parallel.tobytes() == serial.tobytes()


def test_covref_par1_full_reference_is_scientifically_identical(tmp_path: Path) -> None:
    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    serial = mdstats.build_target_coverage_reference(
        data4, data5, data6, freeze, audit, query_workers=1
    )
    parallel = mdstats.build_target_coverage_reference(
        data4,
        data5,
        data6,
        freeze,
        audit,
        query_workers=1,
        execution_scope=_scope(3),
    )
    assert parallel.content_digest == serial.content_digest
    assert parallel.to_dict() == serial.to_dict()
    for serial_domain, parallel_domain in zip(serial.domains, parallel.domains, strict=True):
        for serial_family, parallel_family in zip(serial_domain.families, parallel_domain.families, strict=True):
            assert parallel_family.local_radii.tobytes() == serial_family.local_radii.tobytes()
            assert parallel_family.scales.tobytes() == serial_family.scales.tobytes()
            assert parallel_family.weights.tobytes() == serial_family.weights.tobytes()


def test_covref_par1_rejects_nested_native_tree_parallelism(tmp_path: Path) -> None:
    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    with pytest.raises(mdstats.TrainingDataInputError, match="query_workers=1"):
        mdstats.build_target_coverage_reference(
            data4,
            data5,
            data6,
            freeze,
            audit,
            query_workers=2,
            execution_scope=_scope(2),
        )


def test_covref_par1_campaign_parallelism_uses_full_configured_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    from mdstats.training_data import campaign_cli

    class _Resources:
        cpu_threads_budget = 7
        cpu_threads_available = 8

    monkeypatch.setattr(campaign_cli, "detect_system_resources", lambda **kwargs: _Resources())
    workers, resources = campaign_cli._target_coverage_reference_parallelism(
        {"performance": {"target_coverage_workers": 0}}
    )
    assert workers == 7
    assert resources.cpu_threads_budget == 7
    explicit, _ = campaign_cli._target_coverage_reference_parallelism(
        {"performance": {"target_coverage_workers": 5}}
    )
    assert explicit == 5
