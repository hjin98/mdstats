from __future__ import annotations

import re
from pathlib import Path

import pytest

from mdstats.training_data.progress_timing import (
    PROGRESS_TIME_UNKNOWN,
    format_progress_fraction,
    format_progress_rate,
    format_progress_time,
    format_progress_timing_fields,
)


_TIME_RE = re.compile(r"^(?:\d{2,}:\d{2}:\d{2}|--:--:--)$")


def test_mlff_progress_time_is_fixed_width_hh_mm_ss() -> None:
    assert format_progress_time(None) == PROGRESS_TIME_UNKNOWN == "--:--:--"
    assert format_progress_time(float("inf")) == "--:--:--"
    assert format_progress_time(-1.0) == "--:--:--"
    assert format_progress_time(0.0) == "00:00:00"
    assert format_progress_time(9.6) == "00:00:10"
    assert format_progress_time(65.0) == "00:01:05"
    assert format_progress_time(3661.0) == "01:01:01"
    assert format_progress_time(100 * 3600 + 2) == "100:00:02"


def test_mlff_progress_fraction_and_rates_use_canonical_fields() -> None:
    assert format_progress_fraction(128, 36759) == "128/36,759 (0.3%)"
    assert format_progress_fraction(0, 0) == "0/0 (100.0%)"
    assert format_progress_rate(17.053, "frame/s") == "17.05 frame/s"
    assert format_progress_rate(0.0, "frame/s") == "-- frame/s"
    with pytest.raises(ValueError):
        format_progress_fraction(2, 1)


def test_mlff_progress_timing_field_order_is_stable() -> None:
    message = format_progress_timing_fields(
        elapsed_seconds=65.0,
        eta_seconds=3661.0,
        recent_rate=17.053,
        average_rate=16.5,
        rate_unit="frame/s",
    )
    assert message == (
        "elapsed=00:01:05; eta=01:01:01; "
        "recent=17.05 frame/s; avg=16.50 frame/s"
    )


def test_mlff_source_contains_no_legacy_eta_dialects() -> None:
    root = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"
    offenders: list[str] = []
    forbidden = (
        "eta=estimating",
        "recent=estimating",
        "eta={timing.eta_seconds / 60.0",
        "eta={remaining/rate",
    )
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.name}: {token}")
    assert not offenders, offenders


def test_all_literal_mlff_eta_placeholders_are_hh_mm_ss() -> None:
    root = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"
    # Literal eta values are used only for start/unknown/complete states.  Any
    # calculated ETA must go through format_progress_time().
    literal = re.compile(r"(?<![A-Za-z])eta=([^;\"'}]+)")
    offenders: list[str] = []
    for path in root.glob("*.py"):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.lstrip().startswith(("#", "\"\"\"")):
                continue
            if 'f"' not in line and "f'" not in line:
                continue
            if not re.search(r'(?<![A-Za-z])eta=', line) or "format_progress_time" in line:
                continue
            for match in literal.finditer(line):
                value = match.group(1).strip()
                if value.startswith("{"):
                    continue
                if not _TIME_RE.match(value):
                    offenders.append(f"{path.name}:{line_number}: {value}")
    assert not offenders, offenders
