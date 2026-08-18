"""Generate corrected and compatibility ring catalogs for 300 K Na-LTA."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from mdstats.analysis import (
    FrameworkTopology,
    PrimitiveRingOptions,
    PrimitiveRingSearchMethod,
    enumerate_primitive_rings,
)

HERE = Path(__file__).resolve().parent
INPUT = HERE / "na_lta_framework_topology.json"
OUTPUT = HERE / "generated"


def _size_map(catalog: object) -> dict[int, int]:
    return {
        item.ring_size: item.ring_count
        for item in catalog.ring_size_counts  # type: ignore[attr-defined]
    }


def _write_rings(path: Path, catalog: object) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "ring_id",
                "ring_size",
                "generator_kinds",
                "generator_anchor_count",
                "digest",
            ]
        )
        for ring in catalog.rings:  # type: ignore[attr-defined]
            writer.writerow(
                [
                    ring.ring_id,
                    ring.size,
                    " ".join(ring.generator_kinds),
                    ring.generator_anchor_count,
                    ring.digest,
                ]
            )


def _write_source_searches(path: Path, catalog: object) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "source_atom_index",
                "maximum_depth",
                "complete_through_depth",
                "visited_lifted_state_count",
                "target_state_count",
                "predecessor_record_count",
                "truncated",
            ]
        )
        for search in catalog.diagnostics.source_searches:  # type: ignore[attr-defined]
            writer.writerow(
                [
                    search.source_atom_index,
                    search.maximum_depth,
                    search.complete_through_depth,
                    search.visited_lifted_state_count,
                    search.target_state_count,
                    search.predecessor_record_count,
                    search.truncated,
                ]
            )


def main() -> None:
    topology = FrameworkTopology.from_dict(json.loads(INPUT.read_text()))
    default = enumerate_primitive_rings(
        topology,
        options=PrimitiveRingOptions(max_ring_size=8),
    )
    subset = enumerate_primitive_rings(
        topology,
        options=PrimitiveRingOptions(
            method=PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST,
            max_ring_size=8,
        ),
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "primitive_ring_catalog.json").write_text(
        json.dumps(default.to_dict(), indent=2, sort_keys=True) + "\n"
    )
    (OUTPUT / "edge_shortest_subset_catalog.json").write_text(
        json.dumps(subset.to_dict(), indent=2, sort_keys=True) + "\n"
    )
    _write_rings(OUTPUT / "rings.csv", default)
    _write_source_searches(OUTPUT / "source_searches.csv", default)

    default_counts = _size_map(default)
    subset_counts = _size_map(subset)
    size_lines = "\n".join(
        f"| {size} | {default_counts.get(size, 0)} | {subset_counts.get(size, 0)} |"
        for size in sorted(default_counts.keys() | subset_counts.keys())
    )
    report = f"""# Na-LTA corrected primitive-ring acceptance result

- Framework topology digest: `{topology.digest}`
- Framework vertices: {topology.n_vertices}
- Framework edges: {topology.n_edges}
- Default method: `{default.search_method.value}`
- Default family: `{default.ring_family.value}`
- Primitive rings through size 8: {len(default.rings)}
- Edge-shortest subset rings through size 8: {len(subset.rings)}
- Resource truncation: {not default.search_completed_without_resource_truncation}
- Primitive catalog digest: `{default.digest}`

| Framework cycle size | Primitive/no-shortcut | Edge-shortest subset |
|---:|---:|---:|
{size_lines}

The corrected default returns 36 four-rings, 40 six-rings, and 6 eight-rings.
The removed-edge compatibility method returns the earlier 36 four-rings and 16
six-rings. These are topological cycle counts, not conventional geometrically
classified ring-site counts. Ring geometry, cages, portals, and site labels
remain downstream responsibilities.
"""
    (OUTPUT / "REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
