"""Utilities for safely recovering complete records from interrupted XML streams."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


class InterruptedXmlWarning(UserWarning):
    """Warning emitted when a trailing interrupted XML stream is recovered."""


@dataclass(frozen=True, slots=True)
class XmlInterruptionDiagnostic:
    message: str
    line: int
    column: int
    total_lines: int
    recoverable_trailing_interruption: bool

    @property
    def summary(self) -> str:
        return (
            f"trailing interrupted XML recovered at line {self.line}, column {self.column}: "
            f"{self.message}"
        )


def _line_count(path: Path) -> int:
    count = 0
    last = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            count += chunk.count(b"\n")
            last = chunk[-1:] if chunk else last
    return count + (0 if last in {b"", b"\n"} else 1)


def classify_xml_parse_error(
    path: str | Path,
    error: ET.ParseError,
    *,
    trailing_line_tolerance: int = 2,
) -> XmlInterruptionDiagnostic:
    """Classify whether ``error`` is consistent with interruption at EOF.

    Only parser failures whose diagnostic is interruption-like and whose
    location is at the physical end of the file are recoverable. Structural
    errors in the middle of a file remain hard failures.
    """

    source = Path(path)
    line, column = getattr(error, "position", (0, 0))
    total_lines = _line_count(source)
    text = str(error).lower()
    interruption_markers = (
        "no element found",
        "unclosed token",
        "partial character",
        "unclosed cdata section",
        "unclosed entity reference",
    )
    interruption_like = any(marker in text for marker in interruption_markers)
    near_eof = line >= max(1, total_lines - trailing_line_tolerance)
    return XmlInterruptionDiagnostic(
        message=str(error),
        line=int(line),
        column=int(column),
        total_lines=int(total_lines),
        recoverable_trailing_interruption=bool(interruption_like and near_eof),
    )


__all__ = [
    "InterruptedXmlWarning",
    "XmlInterruptionDiagnostic",
    "classify_xml_parse_error",
]
