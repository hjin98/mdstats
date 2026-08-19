"""Execution-only timing journal for PAR-DENS6 qualification.

The journal is context-local and deliberately absent from scalar-field content
identity, density planning approval IDs, and scientific provenance.  It exists
so production qualification can compare calibrated predictions with observed
preprocessing/planning/realization costs without contaminating the numerical
artifacts being measured.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

DENSITY_EXECUTION_JOURNAL_SCHEMA = "mdstats.density-execution-journal.v1"


@dataclass(slots=True)
class DensityExecutionJournal:
    timings: list[dict[str, Any]] = field(default_factory=list)


_CURRENT: ContextVar[DensityExecutionJournal | None] = ContextVar(
    "mdstats_density_execution_journal", default=None
)


@contextmanager
def density_execution_journal_scope() -> Iterator[DensityExecutionJournal]:
    journal = DensityExecutionJournal()
    token = _CURRENT.set(journal)
    try:
        yield journal
    finally:
        _CURRENT.reset(token)


def record_density_stage_timing(
    *, field_key: str, stage: str, wall_seconds: float, metadata: dict[str, Any] | None = None
) -> None:
    journal = _CURRENT.get()
    if journal is None:
        return
    journal.timings.append(
        {
            "field_key": str(field_key),
            "stage": str(stage),
            "wall_seconds": float(wall_seconds),
            "metadata": {} if metadata is None else dict(metadata),
        }
    )


def density_execution_report(journal: DensityExecutionJournal | None) -> dict[str, Any]:
    timings = [] if journal is None else list(journal.timings)
    totals: dict[str, float] = {}
    for item in timings:
        stage = str(item["stage"])
        totals[stage] = totals.get(stage, 0.0) + float(item["wall_seconds"])
    return {
        "schema_version": DENSITY_EXECUTION_JOURNAL_SCHEMA,
        "timings": timings,
        "stage_totals_seconds": {key: totals[key] for key in sorted(totals)},
    }


__all__ = [
    "DENSITY_EXECUTION_JOURNAL_SCHEMA",
    "DensityExecutionJournal",
    "density_execution_journal_scope",
    "density_execution_report",
    "record_density_stage_timing",
]
