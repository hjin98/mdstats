"""Stable CSV and JSON export for completed topology-statistics results.

The export layer is intentionally non-analytical: every table is assembled from
already validated TS0--TS4 result objects.  It does not inspect source catalogs or
recompute graph descriptors.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


from ..analysis.topology_statistics import (
    AtomicConnectivityStatistics,
    FrameworkTopologyStatistics,
    TopologyStatistics,
)

CANONICAL_TOPOLOGY_STATISTICS_EXPORT_SCHEMA = "mdstats.topology-statistics.export.v1"
ScalarCell = str | int | float | bool | None
StatisticsResult = (
    AtomicConnectivityStatistics | FrameworkTopologyStatistics | TopologyStatistics
)


class TopologyStatisticsExportError(ValueError):
    """Raised when a topology-statistics export request is invalid."""


@dataclass(frozen=True, slots=True)
class TopologyStatisticsTable:
    """One deterministic rectangular table ready for CSV serialization."""

    name: str
    columns: tuple[str, ...]
    rows: tuple[tuple[ScalarCell, ...], ...]

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        columns = tuple(str(value).strip() for value in self.columns)
        rows = tuple(tuple(row) for row in self.rows)
        if not name or not columns or any(not value for value in columns):
            raise TopologyStatisticsExportError(
                "Table name and every column name must be nonempty."
            )
        if len(set(columns)) != len(columns):
            raise TopologyStatisticsExportError("Table columns must be unique.")
        if any(len(row) != len(columns) for row in rows):
            raise TopologyStatisticsExportError(
                "Every table row must match the declared column count."
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "rows", rows)

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    def write_csv(self, path: str | Path, *, overwrite: bool = False) -> Path:
        destination = Path(path)
        _prepare_destination(destination, overwrite=overwrite)
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(self.columns)
            writer.writerows(self.rows)
        return destination


@dataclass(frozen=True, slots=True)
class TopologyStatisticsExportManifest:
    """Files produced by one TS5 export operation."""

    output_directory: Path
    json_path: Path | None
    csv_paths: tuple[Path, ...]
    table_row_counts: Mapping[str, int]
    canonical_schema_version: str = CANONICAL_TOPOLOGY_STATISTICS_EXPORT_SCHEMA


def _prepare_destination(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def _json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _axis_rows(
    result: AtomicConnectivityStatistics | FrameworkTopologyStatistics,
) -> TopologyStatisticsTable:
    axis = result.axis
    rows = []
    for position in range(axis.n_frames):
        rows.append(
            (
                position,
                int(axis.collection_frame_indices[position]),
                int(axis.frame_ids[position]),
                None if axis.steps is None else int(axis.steps[position]),
                None if axis.times is None else float(axis.times[position]),
                axis.time_unit,
            )
        )
    return TopologyStatisticsTable(
        "frame_axis",
        (
            "result_position",
            "collection_frame_index",
            "frame_id",
            "step",
            "time",
            "time_unit",
        ),
        tuple(rows),
    )


def _catalog_tables(
    result: AtomicConnectivityStatistics | FrameworkTopologyStatistics,
    *,
    prefix: str,
) -> list[TopologyStatisticsTable]:
    occupancy = result.catalog_occupancy
    rows = []
    for state_id in range(occupancy.n_states):
        rows.append(
            (
                state_id,
                int(occupancy.state_frame_counts[state_id]),
                float(occupancy.state_probabilities[state_id]),
                int(occupancy.first_result_positions[state_id]),
                int(occupancy.last_result_positions[state_id]),
                None
                if occupancy.visit_counts is None
                else int(occupancy.visit_counts[state_id]),
            )
        )
    assignments = tuple(
        (position, int(state_id))
        for position, state_id in enumerate(occupancy.frame_to_state_id)
    )
    return [
        TopologyStatisticsTable(
            f"{prefix}_catalog_occupancy",
            (
                "state_id",
                "frame_count",
                "probability",
                "first_result_position",
                "last_result_position",
                "visit_count",
            ),
            tuple(rows),
        ),
        TopologyStatisticsTable(
            f"{prefix}_state_assignments",
            ("result_position", "state_id"),
            assignments,
        ),
    ]


def _distribution_rows(
    label: str, distribution: Any
) -> Iterable[tuple[ScalarCell, ...]]:
    for value, frequency, probability in zip(
        distribution.support,
        distribution.frequencies,
        distribution.probabilities,
        strict=True,
    ):
        yield (label, int(value), int(frequency), float(probability))


def _temporal_tables(temporal: Any, *, prefix: str) -> list[TopologyStatisticsTable]:
    if temporal is None:
        return []
    state = temporal.state_statistics
    residence_rows = tuple(
        (
            item.interval_id,
            item.state_id,
            item.result_position_start,
            item.result_position_stop,
            item.n_frames,
            item.time_start,
            item.time_end,
            item.time_span,
        )
        for item in state.residence_intervals
    )
    transition_rows = tuple(
        (
            event.transition_id,
            event.result_position_before,
            event.result_position_after,
            event.source_state_id,
            event.target_state_id,
            event.step_after,
            event.time_after,
        )
        for event in state.transition_events
    )
    return [
        TopologyStatisticsTable(
            f"{prefix}_state_residence",
            (
                "interval_id",
                "state_id",
                "result_position_start",
                "result_position_stop",
                "n_frames",
                "time_start",
                "time_stop",
                "time_span",
            ),
            residence_rows,
        ),
        TopologyStatisticsTable(
            f"{prefix}_state_transitions",
            (
                "transition_id",
                "result_position_before",
                "result_position_after",
                "source_state_id",
                "target_state_id",
                "step_after",
                "time_after",
            ),
            transition_rows,
        ),
    ]


def _atomic_tables(
    result: AtomicConnectivityStatistics,
) -> list[TopologyStatisticsTable]:
    tables = [_axis_rows(result), *_catalog_tables(result, prefix="atomic")]
    tables.append(
        TopologyStatisticsTable(
            "atomic_total_edge_series",
            ("result_position", "total_edge_count"),
            tuple(
                (position, int(value))
                for position, value in enumerate(result.total_edge_series.values)
            ),
        )
    )
    pair_series_rows = []
    pair_distribution_rows = []
    contact_occupancy_rows = []
    for pair in result.pair_statistics:
        pair_series_rows.extend(
            (position, pair.label, int(value))
            for position, value in enumerate(pair.contact_count_series.values)
        )
        pair_distribution_rows.extend(
            _distribution_rows(pair.label, pair.contact_count_distribution)
        )
        if pair.contact_occupancies is not None:
            contact_occupancy_rows.extend(
                (
                    pair.label,
                    item.contact.atom_i,
                    item.contact.atom_j,
                    item.frame_count,
                    item.probability,
                )
                for item in pair.contact_occupancies
            )
    tables.extend(
        [
            TopologyStatisticsTable(
                "atomic_pair_count_series",
                ("result_position", "species_pair", "contact_count"),
                tuple(pair_series_rows),
            ),
            TopologyStatisticsTable(
                "atomic_pair_count_distribution",
                ("species_pair", "count", "frequency", "probability"),
                tuple(pair_distribution_rows),
            ),
            TopologyStatisticsTable(
                "atomic_contact_occupancy",
                ("species_pair", "atom_i", "atom_j", "frame_count", "probability"),
                tuple(contact_occupancy_rows),
            ),
        ]
    )
    tables.extend(_temporal_tables(result.temporal_statistics, prefix="atomic"))
    return tables


def _framework_tables(
    result: FrameworkTopologyStatistics,
) -> list[TopologyStatisticsTable]:
    tables = [_axis_rows(result), *_catalog_tables(result, prefix="framework")]
    descriptor_series_rows = []
    descriptor_distribution_rows = []
    for descriptor in result.graph_descriptors:
        descriptor_series_rows.extend(
            (position, descriptor.descriptor, int(value))
            for position, value in enumerate(descriptor.series.values)
        )
        descriptor_distribution_rows.extend(
            _distribution_rows(descriptor.descriptor, descriptor.distribution)
        )
    endpoint_series_rows = []
    endpoint_distribution_rows = []
    for item in result.endpoint_pair_statistics:
        endpoint_series_rows.extend(
            (position, item.label, int(value))
            for position, value in enumerate(item.edge_count_series.values)
        )
        endpoint_distribution_rows.extend(
            _distribution_rows(item.label, item.edge_count_distribution)
        )
    bridge_series_rows = []
    bridge_distribution_rows = []
    for item in result.bridge_signature_statistics:
        bridge_series_rows.extend(
            (position, item.label, item.signature.rule_id, int(value))
            for position, value in enumerate(item.edge_count_series.values)
        )
        for row in _distribution_rows(item.label, item.edge_count_distribution):
            bridge_distribution_rows.append((row[0], item.signature.rule_id, *row[1:]))
    edge_occupancy_rows = []
    if result.edge_occupancies is not None:
        edge_occupancy_rows = [
            (
                _json_text(item.edge_key.to_dict()),
                item.frame_count,
                item.probability,
            )
            for item in result.edge_occupancies
        ]
    tables.extend(
        [
            TopologyStatisticsTable(
                "framework_descriptor_series",
                ("result_position", "descriptor", "value"),
                tuple(descriptor_series_rows),
            ),
            TopologyStatisticsTable(
                "framework_descriptor_distribution",
                ("descriptor", "value", "frequency", "probability"),
                tuple(descriptor_distribution_rows),
            ),
            TopologyStatisticsTable(
                "framework_endpoint_pair_series",
                ("result_position", "endpoint_pair", "edge_count"),
                tuple(endpoint_series_rows),
            ),
            TopologyStatisticsTable(
                "framework_endpoint_pair_distribution",
                ("endpoint_pair", "count", "frequency", "probability"),
                tuple(endpoint_distribution_rows),
            ),
            TopologyStatisticsTable(
                "framework_bridge_signature_series",
                ("result_position", "bridge_signature", "rule_id", "edge_count"),
                tuple(bridge_series_rows),
            ),
            TopologyStatisticsTable(
                "framework_bridge_signature_distribution",
                ("bridge_signature", "rule_id", "count", "frequency", "probability"),
                tuple(bridge_distribution_rows),
            ),
            TopologyStatisticsTable(
                "framework_edge_occupancy",
                ("edge_key_json", "frame_count", "probability"),
                tuple(edge_occupancy_rows),
            ),
        ]
    )
    tables.extend(_temporal_tables(result.temporal_statistics, prefix="framework"))
    return tables


def _combined_tables(result: TopologyStatistics) -> list[TopologyStatisticsTable]:
    tables = _atomic_tables(result.atomic)
    atomic_axis = tables.pop(0)
    framework_tables = _framework_tables(result.framework)
    framework_tables.pop(0)
    tables = [atomic_axis, *tables, *framework_tables]
    contingency_rows = []
    for atomic_state in range(result.contingency.n_atomic_states):
        for framework_class in range(result.contingency.n_framework_classes):
            contingency_rows.append(
                (
                    atomic_state,
                    framework_class,
                    int(
                        result.contingency.frame_count_matrix[
                            atomic_state, framework_class
                        ]
                    ),
                    float(
                        result.contingency.probability_matrix[
                            atomic_state, framework_class
                        ]
                    ),
                )
            )
    assignments = tuple(
        (
            position,
            int(result.atomic.catalog_occupancy.frame_to_state_id[position]),
            int(result.framework.catalog_occupancy.frame_to_state_id[position]),
        )
        for position in range(result.n_frames)
    )
    tables.extend(
        [
            TopologyStatisticsTable(
                "cross_layer_assignments",
                ("result_position", "atomic_state_id", "framework_class_id"),
                assignments,
            ),
            TopologyStatisticsTable(
                "cross_layer_contingency",
                ("atomic_state_id", "framework_class_id", "frame_count", "probability"),
                tuple(contingency_rows),
            ),
        ]
    )
    if result.boundary_statistics is not None:
        kinds = ("stable", "atomic_only", "framework_only", "coupled")
        rows = tuple(
            (
                position,
                position + 1,
                kinds[int(code)],
            )
            for position, code in enumerate(
                result.boundary_statistics.boundary_kind_codes
            )
        )
        tables.append(
            TopologyStatisticsTable(
                "cross_layer_boundaries",
                ("result_position_before", "result_position_after", "kind"),
                rows,
            )
        )
    return tables


def build_topology_statistics_tables(
    result: StatisticsResult,
) -> tuple[TopologyStatisticsTable, ...]:
    """Return the deterministic initial TS5 table set for one statistics result."""
    if isinstance(result, TopologyStatistics):
        tables = _combined_tables(result)
    elif isinstance(result, AtomicConnectivityStatistics):
        tables = _atomic_tables(result)
    elif isinstance(result, FrameworkTopologyStatistics):
        tables = _framework_tables(result)
    else:
        raise TypeError("Unsupported topology-statistics result type.")
    names = [table.name for table in tables]
    if len(names) != len(set(names)):
        raise TopologyStatisticsExportError("Generated table names are not unique.")
    return tuple(tables)


def write_topology_statistics_json(
    result: StatisticsResult,
    path: str | Path,
    *,
    overwrite: bool = False,
    indent: int = 2,
) -> Path:
    """Write the authoritative statistics result payload as UTF-8 JSON."""
    destination = Path(path)
    _prepare_destination(destination, overwrite=overwrite)
    destination.write_text(
        json.dumps(result.to_dict(), indent=indent, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def export_topology_statistics(
    result: StatisticsResult,
    output_directory: str | Path,
    *,
    prefix: str = "topology_statistics",
    write_json: bool = True,
    write_csv: bool = True,
    overwrite: bool = False,
) -> TopologyStatisticsExportManifest:
    """Export JSON plus deterministic CSV tables and return a manifest."""
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    clean_prefix = str(prefix).strip()
    if not clean_prefix:
        raise TopologyStatisticsExportError("prefix must be nonempty.")
    json_path = None
    if write_json:
        json_path = write_topology_statistics_json(
            result,
            directory / f"{clean_prefix}.json",
            overwrite=overwrite,
        )
    csv_paths: list[Path] = []
    row_counts: dict[str, int] = {}
    if write_csv:
        for table in build_topology_statistics_tables(result):
            path = directory / f"{clean_prefix}_{table.name}.csv"
            csv_paths.append(table.write_csv(path, overwrite=overwrite))
            row_counts[table.name] = table.n_rows
    return TopologyStatisticsExportManifest(
        output_directory=directory.resolve(),
        json_path=None if json_path is None else json_path.resolve(),
        csv_paths=tuple(path.resolve() for path in csv_paths),
        table_row_counts=dict(sorted(row_counts.items())),
    )


__all__ = [
    "CANONICAL_TOPOLOGY_STATISTICS_EXPORT_SCHEMA",
    "TopologyStatisticsExportError",
    "TopologyStatisticsTable",
    "TopologyStatisticsExportManifest",
    "build_topology_statistics_tables",
    "write_topology_statistics_json",
    "export_topology_statistics",
]
