"""Internal source-oriented trajectory representation and I/O helpers."""

from __future__ import annotations

import bz2
import gzip
import lzma
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TextIO

import numpy as np
from numpy.typing import NDArray

CoordinateKind = Literal[
    "unwrapped_fractional",
    "unwrapped_cartesian",
    "wrapped_fractional",
    "wrapped_cartesian",
]


@dataclass(slots=True)
class RawFrameCollection:
    """Internal source-oriented frame collection before normalization.

    All numeric quantities must already be converted to the package's internal
    units.  Atom ordering may still vary by frame when ``source_ids`` is set.
    """

    source_ids: NDArray[np.int64] | None  # (T, N)
    source_type_ids: NDArray[np.int32] | None  # (T, N), source bookkeeping
    atomic_numbers: NDArray[np.int32]  # (T, N)
    masses: NDArray[np.float64]  # (T, N), amu

    frame_ids: NDArray[np.int64]
    steps: NDArray[np.int64] | None
    times: NDArray[np.float64] | None

    cells: NDArray[np.float64]
    origins: NDArray[np.float64]
    pbc: NDArray[np.bool_]

    coordinate_kind: CoordinateKind
    coordinates: NDArray[np.float64]
    image_flags: NDArray[np.int64] | None = None

    velocities: NDArray[np.float64] | None = None
    forces: NDArray[np.float64] | None = None

    stresses: NDArray[np.float64] | None = None
    scalar_pressures: NDArray[np.float64] | None = None
    temperatures: NDArray[np.float64] | None = None
    potential_energies: NDArray[np.float64] | None = None
    kinetic_energies: NDArray[np.float64] | None = None
    total_energies: NDArray[np.float64] | None = None

    source_units: str = "internal"
    metadata: dict[str, Any] = field(default_factory=dict)


def open_text_auto(path: str | Path) -> TextIO:
    """Open plain or gzip/bzip2/xz-compressed text transparently."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    if suffix == ".bz2":
        return bz2.open(path, "rt", encoding="utf-8", errors="replace")
    if suffix in {".xz", ".lzma"}:
        return lzma.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")
