"""LD9-V4 bounded shell-execution contract tests."""
from __future__ import annotations

import pytest

from mdstats import DensityMeshExecutionOptions, DensityMeshExecutionReport


def test_execution_options_round_trip_and_worker_resolution() -> None:
    options = DensityMeshExecutionOptions(
        max_parallel_shell_workers=3,
        worker_native_threads=1,
        worker_timeout_seconds=120.0,
        metadata={"stage": "LD9-V4"},
    )
    restored = DensityMeshExecutionOptions.from_json_dict(options.to_json_dict())
    assert restored == options
    assert restored.resolved_worker_count(0) == 1
    assert restored.resolved_worker_count(1) == 1
    assert restored.resolved_worker_count(2) == 2
    assert restored.resolved_worker_count(12) == 3


def test_execution_options_reject_invalid_limits() -> None:
    with pytest.raises(Exception, match="max_parallel_shell_workers"):
        DensityMeshExecutionOptions(max_parallel_shell_workers=0)
    with pytest.raises(Exception, match="worker_timeout_seconds"):
        DensityMeshExecutionOptions(worker_timeout_seconds=0.0)


def test_execution_report_round_trip_and_efficiency() -> None:
    report = DensityMeshExecutionReport(
        isolated_shell_count=12,
        parallel_worker_count=3,
        wall_seconds=90.0,
        sum_shell_seconds=240.0,
        maximum_shell_seconds=55.0,
        metadata={"scheduler": "test"},
    )
    assert report.parallel_efficiency == pytest.approx(240.0 / 270.0)
    restored = DensityMeshExecutionReport.from_json_dict(report.to_json_dict())
    assert restored == report
