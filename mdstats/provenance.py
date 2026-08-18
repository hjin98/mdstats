"""Provenance records for normalized atomistic frame collections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SourceFormat = Literal[
    "vasp-vasprun-xml",
    "vasp-xdatcar",
    "vasp-contcar-trajectory",
    "lammps-custom-dump",
    "ase-structure",
    "ase-structure-collection",
]
VelocitySource = Literal[
    "native",
    "finite_difference",
    "unavailable",
    "discarded_for_ensemble",
]
CoordinateNormalizationMethod = Literal[
    "native_unwrapped_fractional",
    "native_unwrapped_cartesian",
    "image_flags",
    "minimum_image_inferred",
    "independent_frame_wrapping",
]


@dataclass(frozen=True, slots=True)
class FrameCollectionProvenance:
    """Describe how a source collection was normalized.

    Less structured source-specific details belong in
    :attr:`AtomisticFrameCollection.metadata`.
    """

    source_format: SourceFormat
    source_files: tuple[str, ...]
    velocity_source: VelocitySource
    coordinate_normalization: CoordinateNormalizationMethod
    stress_source: str | None
    units_source: str
    stress_convention: Literal["tensile_positive"] = "tensile_positive"
