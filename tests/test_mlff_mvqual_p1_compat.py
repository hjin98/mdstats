from __future__ import annotations

from types import SimpleNamespace

import pytest

from mdstats.training_data import mvqual_p1_runtime as runtime
from mdstats.training_data import target_multi_view_qualification as mvqual


def _rung(size: int, *uids: str) -> SimpleNamespace:
    return SimpleNamespace(
        target_size=size,
        materializable=True,
        frame_uids=tuple(uids),
    )


def test_p1_wrapper_is_transparent_for_partial_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    progress: list[str] = []

    def canonical_builder(
        target_coverage_reference: object,
        target_coverage_sparse_index: object,
        target_coverage_feasibility: object,
        target_data_role_freeze: object,
        legacy_target_data_ladder: object,
        target_multi_view_repair: object,
        *,
        policy: object = None,
        coverage_query_workers: int = 1,
        scoring_workers: int = 1,
        sparse_max_edges: int = 8,
        resource_scope: object = None,
        execution_telemetry_callback: object = None,
        job_telemetry_callback: object = None,
        progress_callback: object = None,
    ) -> object:
        del (
            target_coverage_reference,
            target_coverage_sparse_index,
            target_coverage_feasibility,
            target_data_role_freeze,
            legacy_target_data_ladder,
            target_multi_view_repair,
            policy,
            coverage_query_workers,
            scoring_workers,
            sparse_max_edges,
            resource_scope,
            execution_telemetry_callback,
            job_telemetry_callback,
            progress_callback,
        )
        return sentinel

    reference = SimpleNamespace(
        # Deliberately matches the historical MEM1 fixture: enough for the
        # canonical MVQUAL builder test double, but not enough for the full
        # TARGET-DATA2B progressive scorer, which requires reference.domain().
        domains=(SimpleNamespace(label_domain_id="domain-a"),),
    )
    legacy_domain = SimpleNamespace(rungs=(_rung(2, "a", "b"),))
    repair_domain = SimpleNamespace(rungs=(_rung(2, "a", "c"),))
    legacy = SimpleNamespace(domain=lambda label: legacy_domain)
    repair = SimpleNamespace(domain=lambda label: repair_domain)

    monkeypatch.setattr(mvqual, "build_target_multi_view_qualification_plan", canonical_builder)
    fake_mdstats = SimpleNamespace(
        build_target_multi_view_qualification_plan=canonical_builder
    )
    runtime.install_mvqual_p1_runtime(fake_mdstats)

    result = fake_mdstats.build_target_multi_view_qualification_plan(
        reference,
        object(),
        object(),
        object(),
        legacy,
        repair,
        progress_callback=progress.append,
    )

    assert result is sentinel
    assert progress == []
    assert runtime.last_mvqual_p1_execution_telemetry() is None
