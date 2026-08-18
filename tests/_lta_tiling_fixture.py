from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from mdstats.analysis import (
    build_lta_natural_tiling_reference,
    build_tiling_geometry_catalog,
)
from mdstats.analysis.framework_topology import FrameworkTopology

DATA = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def lta_reference_geometry():
    """Build the expensive exact LTA tiling/geometry fixture once per test process."""

    topology = FrameworkTopology.from_dict(
        json.loads((DATA / "na_lta_framework_topology.json").read_text())
    )
    reference = build_lta_natural_tiling_reference(topology)
    geometry = build_tiling_geometry_catalog(
        reference.complex,
        reference.embedding,
        reference.ring_index,
    )
    return topology, reference, geometry
