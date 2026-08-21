"""P1 execution-only progressive TARGET-DATA2B reuse for MVQUAL1.

The scientific MVQUAL owner remains :mod:`target_multi_view_qualification`.
This module installs only an execution seam: before that owner evaluates its
per-rung sparse/hard jobs, exact direct TARGET-DATA2B reports are produced once
per nested ``(domain, selector)`` sequence by the existing
``score_target_nested_subsets_coverage`` semantic owner.  During the unchanged
MVQUAL builder call, matching independent-score requests are satisfied from
those exact reports.  Nonnested sequences fall back to the historical
independent scorer without redefining nesting.

No cached report, timing, worker choice, or fallback decision is scientific
state and none enters an mdstats content digest.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass
from functools import wraps
import inspect
import threading
import time
from typing import Any, Callable, Mapping, Sequence

from . import target_coverage as _coverage
from . import target_multi_view_qualification as _mvqual
from .progress_timing import format_progress_time
from .resources import stage_resource_scope


@dataclass(frozen=True, slots=True)
class MvqualP1ExecutionTelemetry:
    """Bounded execution telemetry for one progressive-direct prepass."""

    group_count: int
    progressive_group_count: int
    fallback_group_count: int
    requested_workers: int
    effective_workers: int
    report_count: int
    wall_seconds: float
    group_seconds: tuple[tuple[str, str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_count": int(self.group_count),
            "progressive_group_count": int(self.progressive_group_count),
            "fallback_group_count": int(self.fallback_group_count),
            "requested_workers": int(self.requested_workers),
            "effective_workers": int(self.effective_workers),
            "report_count": int(self.report_count),
            "wall_seconds": float(self.wall_seconds),
            "wall_hhmmss": format_progress_time(self.wall_seconds),
            "group_seconds": [
                {
                    "label_domain_id": label,
                    "selector": selector,
                    "wall_seconds": float(seconds),
                    "wall_hhmmss": format_progress_time(seconds),
                }
                for label, selector, seconds in self.group_seconds
            ],
        }


@dataclass(frozen=True, slots=True)
class _ProgressiveGroup:
    domain_index: int
    label_domain_id: str
    selector: str
    sizes: tuple[int, ...]
    selected_frame_uids: tuple[tuple[str, ...], ...]


_INSTALL_LOCK = threading.RLock()
_LAST_TELEMETRY: MvqualP1ExecutionTelemetry | None = None


def last_mvqual_p1_execution_telemetry() -> MvqualP1ExecutionTelemetry | None:
    """Return the most recent P1 execution telemetry, if any."""

    return _LAST_TELEMETRY


def _canonical_selected(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(str(value) for value in values))


def _is_exact_nested_sequence(values: Sequence[Sequence[str]]) -> bool:
    """Match TARGET-DATA2B progressive set-nesting without changing policy."""

    previous: frozenset[str] = frozenset()
    for raw in values:
        selected = tuple(str(value) for value in raw)
        if not selected or len(selected) != len(set(selected)):
            return False
        current = frozenset(selected)
        if not previous.issubset(current):
            return False
        previous = current
    return bool(values)


def _qualification_groups(
    target_coverage_reference: Any,
    legacy_target_data_ladder: Any,
    target_multi_view_repair: Any,
) -> tuple[_ProgressiveGroup, ...]:
    """Reconstruct exactly the direct-score rung sets consumed by MVQUAL1."""

    groups: list[_ProgressiveGroup] = []
    for domain_index, reference_domain in enumerate(target_coverage_reference.domains):
        label = str(reference_domain.label_domain_id)
        legacy_domain = legacy_target_data_ladder.domain(label)
        repair_domain = target_multi_view_repair.domain(label)
        legacy_rungs = {
            int(rung.target_size): rung
            for rung in legacy_domain.rungs
            if bool(rung.materializable)
        }
        mv_rungs = {
            int(rung.target_size): rung
            for rung in repair_domain.rungs
            if bool(rung.materializable)
        }
        common = tuple(sorted(set(legacy_rungs) & set(mv_rungs)))
        if not common:
            # Preserve the canonical MVQUAL owner's error authority.  Do not
            # invent a P1-specific failure before the original builder runs.
            continue
        legacy_sizes = common
        mv_sizes = tuple(sorted(mv_rungs))
        groups.append(
            _ProgressiveGroup(
                domain_index=domain_index,
                label_domain_id=label,
                selector="legacy",
                sizes=legacy_sizes,
                selected_frame_uids=tuple(
                    tuple(str(uid) for uid in legacy_rungs[size].frame_uids)
                    for size in legacy_sizes
                ),
            )
        )
        groups.append(
            _ProgressiveGroup(
                domain_index=domain_index,
                label_domain_id=label,
                selector="mv",
                sizes=mv_sizes,
                selected_frame_uids=tuple(
                    tuple(str(uid) for uid in mv_rungs[size].frame_uids)
                    for size in mv_sizes
                ),
            )
        )
    return tuple(groups)


def _progressive_direct_report_cache(
    target_coverage_reference: Any,
    legacy_target_data_ladder: Any,
    target_multi_view_repair: Any,
    *,
    coverage_query_workers: int,
    scoring_workers: int,
    resource_scope: Any = None,
    scorer: Callable[..., Sequence[Any]] = _coverage.score_target_nested_subsets_coverage,
) -> tuple[dict[tuple[str, tuple[str, ...]], Any], MvqualP1ExecutionTelemetry]:
    """Build exact reusable direct reports for every truly nested selector group."""

    groups = _qualification_groups(
        target_coverage_reference,
        legacy_target_data_ladder,
        target_multi_view_repair,
    )
    progressive = tuple(
        group
        for group in groups
        if _is_exact_nested_sequence(group.selected_frame_uids)
    )
    fallback_count = len(groups) - len(progressive)
    requested = max(1, int(scoring_workers))
    effective = max(1, min(requested, len(progressive))) if progressive else 1
    if resource_scope is not None:
        effective = min(effective, max(1, int(resource_scope.python_workers)))
    inner_query_workers = int(coverage_query_workers) if effective == 1 else 1

    cache: dict[tuple[str, tuple[str, ...]], Any] = {}
    group_seconds: list[tuple[str, str, float]] = []
    started = time.perf_counter()

    def run(group: _ProgressiveGroup) -> tuple[_ProgressiveGroup, tuple[Any, ...], float]:
        group_started = time.perf_counter()
        reports = tuple(
            scorer(
                target_coverage_reference,
                group.label_domain_id,
                group.selected_frame_uids,
                query_workers=inner_query_workers,
            )
        )
        elapsed = time.perf_counter() - group_started
        if len(reports) != len(group.sizes):
            raise _mvqual.TrainingDataInputError(
                "TARGET-DATA2C-MVQUAL-P1 progressive direct scorer returned the wrong rung count."
            )
        for selected_uids, report in zip(group.selected_frame_uids, reports, strict=True):
            expected = _canonical_selected(selected_uids)
            observed = _canonical_selected(report.selected_frame_uids)
            if observed != expected:
                raise _mvqual.TrainingDataInputError(
                    "TARGET-DATA2C-MVQUAL-P1 progressive direct report changed selected membership."
                )
        return group, reports, elapsed

    if progressive:
        if effective == 1:
            completed = [run(group) for group in progressive]
        else:
            scope_context = (
                nullcontext()
                if resource_scope is None
                else stage_resource_scope(
                    _mvqual._mvqual_parallel_scope(resource_scope, effective)
                )
            )
            with scope_context:
                with ThreadPoolExecutor(
                    max_workers=effective,
                    thread_name_prefix="mdstats-mvqual-p1-direct",
                ) as executor:
                    # Futures are consumed in canonical group order so any
                    # failure is surfaced deterministically even though work
                    # executes concurrently.
                    futures = [executor.submit(run, group) for group in progressive]
                    completed = [future.result() for future in futures]

        for group, reports, elapsed in completed:
            group_seconds.append((group.label_domain_id, group.selector, elapsed))
            for selected_uids, report in zip(
                group.selected_frame_uids, reports, strict=True
            ):
                key = (group.label_domain_id, _canonical_selected(selected_uids))
                existing = cache.get(key)
                if existing is not None and existing.content_digest != report.content_digest:
                    raise _mvqual.TrainingDataInputError(
                        "TARGET-DATA2C-MVQUAL-P1 identical selected membership produced different direct reports."
                    )
                cache[key] = report

    wall = time.perf_counter() - started
    telemetry = MvqualP1ExecutionTelemetry(
        group_count=len(groups),
        progressive_group_count=len(progressive),
        fallback_group_count=fallback_count,
        requested_workers=requested,
        effective_workers=effective,
        report_count=len(cache),
        wall_seconds=wall,
        group_seconds=tuple(group_seconds),
    )
    return cache, telemetry


def _install_builder_wrapper(mdstats_module: Any) -> None:
    global _LAST_TELEMETRY

    current = _mvqual.build_target_multi_view_qualification_plan
    if bool(getattr(current, "_mdstats_mvqual_p1_installed", False)):
        if getattr(mdstats_module, "build_target_multi_view_qualification_plan", None) is not current:
            mdstats_module.build_target_multi_view_qualification_plan = current
        return

    original_builder = current
    original_independent_scorer = _mvqual.score_target_subset_coverage
    signature = inspect.signature(original_builder)

    @wraps(original_builder)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        global _LAST_TELEMETRY
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        values: Mapping[str, Any] = bound.arguments
        target_reference = values["target_coverage_reference"]
        legacy_ladder = values["legacy_target_data_ladder"]
        repair_plan = values["target_multi_view_repair"]
        query_workers = int(values["coverage_query_workers"])
        scoring_workers = int(values["scoring_workers"])
        resource_scope = values.get("resource_scope")
        progress_callback = values.get("progress_callback")

        # The underlying MVQUAL builder resolves its direct scorer through this
        # module global.  Protect the temporary execution cache for the complete
        # call so concurrent independent builder invocations cannot observe a
        # partially installed cache.
        with _INSTALL_LOCK:
            try:
                cache, telemetry = _progressive_direct_report_cache(
                    target_reference,
                    legacy_ladder,
                    repair_plan,
                    coverage_query_workers=query_workers,
                    scoring_workers=scoring_workers,
                    resource_scope=resource_scope,
                )
            except AttributeError:
                # The campaign path supplies a canonical TargetCoverageReference.
                # Focused unit tests and third-party callers may intentionally use
                # a partial duck-typed authority while replacing the downstream
                # MVQUAL job evaluator.  P1 is an optional execution seam, so it
                # must be transparent for those noncanonical objects rather than
                # strengthening the public builder's input contract.  Never hide
                # an AttributeError from a real persisted authority.
                if isinstance(target_reference, _coverage.TargetCoverageReference):
                    raise
                _LAST_TELEMETRY = None
                return original_builder(*args, **kwargs)

            _LAST_TELEMETRY = telemetry
            if progress_callback is not None:
                progress_callback(
                    "status=p1-direct; "
                    f"groups={telemetry.progressive_group_count}/{telemetry.group_count}; "
                    f"fallback={telemetry.fallback_group_count}; "
                    f"workers={telemetry.effective_workers}; reports={telemetry.report_count}; "
                    f"elapsed={format_progress_time(telemetry.wall_seconds)}"
                )

            @wraps(original_independent_scorer)
            def cached_independent_scorer(
                reference: Any,
                label_domain_id: str,
                selected_frame_uids: Sequence[str],
                *score_args: Any,
                **score_kwargs: Any,
            ) -> Any:
                if reference is target_reference:
                    key = (
                        str(label_domain_id),
                        _canonical_selected(selected_frame_uids),
                    )
                    cached = cache.get(key)
                    if cached is not None:
                        return cached
                return original_independent_scorer(
                    reference,
                    label_domain_id,
                    selected_frame_uids,
                    *score_args,
                    **score_kwargs,
                )

            _mvqual.score_target_subset_coverage = cached_independent_scorer
            try:
                return original_builder(*args, **kwargs)
            finally:
                _mvqual.score_target_subset_coverage = original_independent_scorer

    wrapped._mdstats_mvqual_p1_installed = True  # type: ignore[attr-defined]
    wrapped._mdstats_mvqual_p1_original = original_builder  # type: ignore[attr-defined]
    _mvqual.build_target_multi_view_qualification_plan = wrapped
    mdstats_module.build_target_multi_view_qualification_plan = wrapped


def install_mvqual_p1_runtime(mdstats_module: Any) -> None:
    """Install P1 execution reuse without changing MVQUAL scientific authority."""

    _install_builder_wrapper(mdstats_module)
