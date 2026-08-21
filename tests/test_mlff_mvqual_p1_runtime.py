from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

import pytest

from mdstats.training_data import mvqual_p1_runtime as runtime
from mdstats.training_data import target_multi_view_qualification as mvqual


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _rung(size: int, *uids: str) -> SimpleNamespace:
    return SimpleNamespace(
        target_size=size,
        materializable=True,
        frame_uids=tuple(uids),
    )


def _group_fixture(*, nonnested_mv: bool = False) -> tuple[object, object, object]:
    reference = SimpleNamespace(
        domains=(SimpleNamespace(label_domain_id="domain-a"),),
    )
    legacy_domain = SimpleNamespace(
        rungs=(
            _rung(2, "a", "b"),
            _rung(4, "a", "b", "c", "d"),
        )
    )
    if nonnested_mv:
        mv_rungs = (
            _rung(2, "a", "c"),
            _rung(4, "b", "c", "d", "e"),
            _rung(8, "a", "b", "c", "d", "e", "f", "g", "h"),
        )
    else:
        mv_rungs = (
            _rung(2, "a", "c"),
            _rung(4, "a", "c", "d", "e"),
            _rung(8, "a", "b", "c", "d", "e", "f", "g", "h"),
        )
    repair_domain = SimpleNamespace(rungs=mv_rungs)
    legacy = SimpleNamespace(domain=lambda label: legacy_domain)
    repair = SimpleNamespace(domain=lambda label: repair_domain)
    return reference, legacy, repair


def test_p1_progressive_cache_maps_exact_nested_selector_reports() -> None:
    reference, legacy, repair = _group_fixture()
    calls: list[tuple[str, tuple[tuple[str, ...], ...], int]] = []

    def scorer(
        _reference: object,
        label: str,
        sequences: tuple[tuple[str, ...], ...],
        *,
        query_workers: int,
    ) -> tuple[SimpleNamespace, ...]:
        calls.append((label, tuple(sequences), query_workers))
        return tuple(
            SimpleNamespace(
                selected_frame_uids=tuple(sorted(selected)),
                content_digest=_digest(",".join(sorted(selected))),
            )
            for selected in sequences
        )

    cache, telemetry = runtime._progressive_direct_report_cache(
        reference,
        legacy,
        repair,
        coverage_query_workers=3,
        scoring_workers=1,
        scorer=scorer,
    )

    assert len(calls) == 2
    assert all(call[2] == 3 for call in calls)
    assert telemetry.group_count == 2
    assert telemetry.progressive_group_count == 2
    assert telemetry.fallback_group_count == 0
    assert telemetry.report_count == 5
    assert set(cache) == {
        ("domain-a", ("a", "b")),
        ("domain-a", ("a", "b", "c", "d")),
        ("domain-a", ("a", "c")),
        ("domain-a", ("a", "c", "d", "e")),
        ("domain-a", ("a", "b", "c", "d", "e", "f", "g", "h")),
    }


def test_p1_nonnested_selector_falls_back_without_redefining_nesting() -> None:
    reference, legacy, repair = _group_fixture(nonnested_mv=True)
    calls: list[tuple[tuple[str, ...], ...]] = []

    def scorer(
        _reference: object,
        _label: str,
        sequences: tuple[tuple[str, ...], ...],
        *,
        query_workers: int,
    ) -> tuple[SimpleNamespace, ...]:
        del query_workers
        calls.append(tuple(sequences))
        return tuple(
            SimpleNamespace(
                selected_frame_uids=tuple(sorted(selected)),
                content_digest=_digest(",".join(sorted(selected))),
            )
            for selected in sequences
        )

    cache, telemetry = runtime._progressive_direct_report_cache(
        reference,
        legacy,
        repair,
        coverage_query_workers=1,
        scoring_workers=4,
        scorer=scorer,
    )

    # Only the legacy sequence is progressive; the nonnested MV sequence is
    # deliberately absent so the canonical builder must use its historical
    # independent direct scorer for those rungs.
    assert len(calls) == 1
    assert calls[0] == (("a", "b"), ("a", "b", "c", "d"))
    assert telemetry.group_count == 2
    assert telemetry.progressive_group_count == 1
    assert telemetry.fallback_group_count == 1
    assert telemetry.report_count == 2
    assert all(key[1] in {("a", "b"), ("a", "b", "c", "d")} for key in cache)


def test_p1_cache_rejects_progressive_membership_drift() -> None:
    reference, legacy, repair = _group_fixture()

    def bad_scorer(
        _reference: object,
        _label: str,
        sequences: tuple[tuple[str, ...], ...],
        *,
        query_workers: int,
    ) -> tuple[SimpleNamespace, ...]:
        del query_workers
        return tuple(
            SimpleNamespace(
                selected_frame_uids=("wrong",),
                content_digest=_digest("wrong"),
            )
            for _ in sequences
        )

    with pytest.raises(mvqual.TrainingDataInputError, match="changed selected membership"):
        runtime._progressive_direct_report_cache(
            reference,
            legacy,
            repair,
            coverage_query_workers=1,
            scoring_workers=1,
            scorer=bad_scorer,
        )


def test_p1_installer_serves_cached_report_to_canonical_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = object()
    legacy = object()
    repair = object()
    sentinel = SimpleNamespace(
        selected_frame_uids=("a", "b"),
        content_digest=_digest("sentinel"),
    )
    independent_calls: list[tuple[str, tuple[str, ...]]] = []
    progress: list[str] = []

    def independent(
        _reference: object,
        label: str,
        selected: tuple[str, ...],
        *,
        query_workers: int,
    ) -> object:
        del query_workers
        independent_calls.append((label, tuple(selected)))
        return SimpleNamespace(content_digest=_digest("fallback"))

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
            target_coverage_sparse_index,
            target_coverage_feasibility,
            target_data_role_freeze,
            legacy_target_data_ladder,
            target_multi_view_repair,
            policy,
            scoring_workers,
            sparse_max_edges,
            resource_scope,
            execution_telemetry_callback,
            job_telemetry_callback,
            progress_callback,
        )
        return mvqual.score_target_subset_coverage(
            target_coverage_reference,
            "domain-a",
            ("b", "a"),
            query_workers=coverage_query_workers,
        )

    telemetry = runtime.MvqualP1ExecutionTelemetry(
        group_count=2,
        progressive_group_count=2,
        fallback_group_count=0,
        requested_workers=4,
        effective_workers=2,
        report_count=1,
        wall_seconds=0.125,
        group_seconds=(("domain-a", "mv", 0.125),),
    )

    def fake_cache(*args: object, **kwargs: object) -> tuple[dict[tuple[str, tuple[str, ...]], object], object]:
        del args, kwargs
        return {("domain-a", ("a", "b")): sentinel}, telemetry

    monkeypatch.setattr(mvqual, "build_target_multi_view_qualification_plan", canonical_builder)
    monkeypatch.setattr(mvqual, "score_target_subset_coverage", independent)
    monkeypatch.setattr(runtime, "_progressive_direct_report_cache", fake_cache)
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
        coverage_query_workers=1,
        scoring_workers=4,
        progress_callback=progress.append,
    )

    assert result is sentinel
    assert independent_calls == []
    assert progress and "status=p1-direct" in progress[0]
    assert runtime.last_mvqual_p1_execution_telemetry() == telemetry
