"""Hard browser-budget contracts for interactive density rendering.

This module implements the LD9-V0 resource contract.  It deliberately does not
extract, simplify, or serialize meshes.  Instead it provides immutable budget and
usage records, exact post-replication accounting, and a structured exception that
renderers can raise before writing an oversized HTML artifact.

The scene-wide budgeting policy and failure semantics are project-specific.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError

BROWSER_MESH_BUDGET_SCHEMA = "mdstats.browser-mesh-budget.v1"
BROWSER_MESH_TRACE_USAGE_SCHEMA = "mdstats.browser-mesh-trace-usage.v1"
BROWSER_MESH_USAGE_SCHEMA = "mdstats.browser-mesh-usage.v1"
BROWSER_MESH_BUDGET_REPORT_SCHEMA = "mdstats.browser-mesh-budget-report.v1"

INTERACTIVE_BROWSER_PROFILE = "interactive_browser"
RAW_REFERENCE_PROFILE = "raw_reference"

DEFAULT_MAX_FINAL_DENSITY_FACES = 300_000
DEFAULT_MAX_FINAL_DENSITY_VERTICES = 200_000
DEFAULT_MAX_FINAL_HTML_BYTES = 40 * 1024**2
DEFAULT_MAX_PLOTLY_TRACES = 64


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


@dataclass(frozen=True, slots=True)
class BrowserMeshBudget:
    """Hard output limits for one complete browser-rendered density scene."""

    max_final_density_faces: int = DEFAULT_MAX_FINAL_DENSITY_FACES
    max_final_density_vertices: int = DEFAULT_MAX_FINAL_DENSITY_VERTICES
    max_final_html_bytes: int = DEFAULT_MAX_FINAL_HTML_BYTES
    max_plotly_traces: int = DEFAULT_MAX_PLOTLY_TRACES
    apply_after_display_replication: bool = True
    hard_limit: bool = True
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = BROWSER_MESH_BUDGET_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BROWSER_MESH_BUDGET_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported browser-mesh-budget schema {self.schema_version!r}."
            )
        object.__setattr__(
            self,
            "max_final_density_faces",
            _positive_int(
                self.max_final_density_faces, name="max_final_density_faces"
            ),
        )
        object.__setattr__(
            self,
            "max_final_density_vertices",
            _positive_int(
                self.max_final_density_vertices, name="max_final_density_vertices"
            ),
        )
        object.__setattr__(
            self,
            "max_final_html_bytes",
            _positive_int(self.max_final_html_bytes, name="max_final_html_bytes"),
        )
        object.__setattr__(
            self,
            "max_plotly_traces",
            _positive_int(self.max_plotly_traces, name="max_plotly_traces"),
        )
        object.__setattr__(
            self,
            "apply_after_display_replication",
            bool(self.apply_after_display_replication),
        )
        object.__setattr__(self, "hard_limit", bool(self.hard_limit))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def validate_for_profile(self, profile: str) -> None:
        if profile not in {INTERACTIVE_BROWSER_PROFILE, RAW_REFERENCE_PROFILE}:
            raise GraphStyleError(f"Unknown density render profile {profile!r}.")
        if profile == INTERACTIVE_BROWSER_PROFILE:
            if not self.hard_limit:
                raise GraphStyleError(
                    "interactive_browser requires BrowserMeshBudget.hard_limit=True."
                )
            if not self.apply_after_display_replication:
                raise GraphStyleError(
                    "interactive_browser requires post-replication budget accounting."
                )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_final_density_faces": self.max_final_density_faces,
            "max_final_density_vertices": self.max_final_density_vertices,
            "max_final_html_bytes": self.max_final_html_bytes,
            "max_plotly_traces": self.max_plotly_traces,
            "apply_after_display_replication": self.apply_after_display_replication,
            "hard_limit": self.hard_limit,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "BrowserMeshBudget":
        return cls(
            max_final_density_faces=value["max_final_density_faces"],
            max_final_density_vertices=value["max_final_density_vertices"],
            max_final_html_bytes=value["max_final_html_bytes"],
            max_plotly_traces=value["max_plotly_traces"],
            apply_after_display_replication=value[
                "apply_after_display_replication"
            ],
            hard_limit=value["hard_limit"],
            metadata=value.get("metadata", {}),
            schema_version=value.get("schema_version", BROWSER_MESH_BUDGET_SCHEMA),
        )


@dataclass(frozen=True, slots=True)
class BrowserMeshTraceUsage:
    """Geometry and replication accounting for one density-mesh trace."""

    trace_key: str
    face_count: int
    vertex_count: int
    display_replication: int = 1
    retained_array_bytes: int = 0
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = BROWSER_MESH_TRACE_USAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BROWSER_MESH_TRACE_USAGE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported browser-mesh-trace-usage schema {self.schema_version!r}."
            )
        if not isinstance(self.trace_key, str) or not self.trace_key:
            raise GraphAdapterError("trace_key must be a nonempty string.")
        object.__setattr__(
            self,
            "face_count",
            _positive_int(self.face_count, name="face_count", minimum=0),
        )
        object.__setattr__(
            self,
            "vertex_count",
            _positive_int(self.vertex_count, name="vertex_count", minimum=0),
        )
        object.__setattr__(
            self,
            "display_replication",
            _positive_int(self.display_replication, name="display_replication"),
        )
        object.__setattr__(
            self,
            "retained_array_bytes",
            _positive_int(
                self.retained_array_bytes, name="retained_array_bytes", minimum=0
            ),
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def serialized_face_count(self) -> int:
        return self.face_count * self.display_replication

    @property
    def serialized_vertex_count(self) -> int:
        return self.vertex_count * self.display_replication

    @property
    def serialized_array_bytes(self) -> int:
        return self.retained_array_bytes * self.display_replication

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_key": self.trace_key,
            "face_count": self.face_count,
            "vertex_count": self.vertex_count,
            "display_replication": self.display_replication,
            "serialized_face_count": self.serialized_face_count,
            "serialized_vertex_count": self.serialized_vertex_count,
            "retained_array_bytes": self.retained_array_bytes,
            "serialized_array_bytes": self.serialized_array_bytes,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "BrowserMeshTraceUsage":
        return cls(
            trace_key=value["trace_key"],
            face_count=value["face_count"],
            vertex_count=value["vertex_count"],
            display_replication=value.get("display_replication", 1),
            retained_array_bytes=value.get("retained_array_bytes", 0),
            metadata=value.get("metadata", {}),
            schema_version=value.get(
                "schema_version", BROWSER_MESH_TRACE_USAGE_SCHEMA
            ),
        )


@dataclass(frozen=True, slots=True)
class BrowserMeshUsage:
    """Complete post-replication browser resource usage for one scene."""

    density_traces: tuple[BrowserMeshTraceUsage, ...]
    non_density_trace_count: int = 0
    final_html_bytes: int | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = BROWSER_MESH_USAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BROWSER_MESH_USAGE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported browser-mesh-usage schema {self.schema_version!r}."
            )
        traces = tuple(self.density_traces)
        if any(not isinstance(item, BrowserMeshTraceUsage) for item in traces):
            raise TypeError("density_traces must contain BrowserMeshTraceUsage records.")
        keys = [item.trace_key for item in traces]
        if len(set(keys)) != len(keys):
            raise GraphAdapterError("density trace keys must be unique.")
        object.__setattr__(self, "density_traces", traces)
        object.__setattr__(
            self,
            "non_density_trace_count",
            _positive_int(
                self.non_density_trace_count,
                name="non_density_trace_count",
                minimum=0,
            ),
        )
        if self.final_html_bytes is not None:
            object.__setattr__(
                self,
                "final_html_bytes",
                _positive_int(
                    self.final_html_bytes, name="final_html_bytes", minimum=0
                ),
            )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def final_density_face_count(self) -> int:
        return sum(item.serialized_face_count for item in self.density_traces)

    @property
    def final_density_vertex_count(self) -> int:
        return sum(item.serialized_vertex_count for item in self.density_traces)

    @property
    def plotly_trace_count(self) -> int:
        return (
            sum(item.display_replication for item in self.density_traces)
            + self.non_density_trace_count
        )

    @property
    def retained_density_array_bytes(self) -> int:
        return sum(item.serialized_array_bytes for item in self.density_traces)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "density_traces": [item.to_json_dict() for item in self.density_traces],
            "non_density_trace_count": self.non_density_trace_count,
            "final_density_face_count": self.final_density_face_count,
            "final_density_vertex_count": self.final_density_vertex_count,
            "plotly_trace_count": self.plotly_trace_count,
            "retained_density_array_bytes": self.retained_density_array_bytes,
            "final_html_bytes": self.final_html_bytes,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "BrowserMeshUsage":
        return cls(
            density_traces=tuple(
                BrowserMeshTraceUsage.from_json_dict(item)
                for item in value.get("density_traces", ())
            ),
            non_density_trace_count=value.get("non_density_trace_count", 0),
            final_html_bytes=value.get("final_html_bytes"),
            metadata=value.get("metadata", {}),
            schema_version=value.get("schema_version", BROWSER_MESH_USAGE_SCHEMA),
        )


@dataclass(frozen=True, slots=True)
class BrowserMeshBudgetReport:
    """Deterministic comparison between one usage record and one hard budget."""

    profile: Literal["interactive_browser", "raw_reference"]
    budget: BrowserMeshBudget
    usage: BrowserMeshUsage
    violations: tuple[str, ...]
    schema_version: str = BROWSER_MESH_BUDGET_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BROWSER_MESH_BUDGET_REPORT_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported browser-mesh-budget-report schema {self.schema_version!r}."
            )
        self.budget.validate_for_profile(self.profile)
        violations = tuple(str(value) for value in self.violations)
        object.__setattr__(self, "violations", violations)

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile": self.profile,
            "passed": self.passed,
            "violations": list(self.violations),
            "budget": self.budget.to_json_dict(),
            "usage": self.usage.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "BrowserMeshBudgetReport":
        return cls(
            profile=value["profile"],
            budget=BrowserMeshBudget.from_json_dict(value["budget"]),
            usage=BrowserMeshUsage.from_json_dict(value["usage"]),
            violations=tuple(value.get("violations", ())),
            schema_version=value.get(
                "schema_version", BROWSER_MESH_BUDGET_REPORT_SCHEMA
            ),
        )


class BrowserMeshBudgetFailure(GraphComplexityError):
    """Raised before serialization when an interactive scene exceeds hard limits."""

    def __init__(self, report: BrowserMeshBudgetReport) -> None:
        if report.passed:
            raise GraphAdapterError("BrowserMeshBudgetFailure requires a failed report.")
        self.report = report
        limits = ", ".join(report.violations)
        super().__init__(
            "Interactive density rendering exceeds the hard browser budget: "
            f"{limits}. No HTML artifact should be written."
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "exception": type(self).__name__,
            "message": str(self),
            "report": self.report.to_json_dict(),
        }


def evaluate_browser_mesh_budget(
    usage: BrowserMeshUsage,
    *,
    budget: BrowserMeshBudget | None = None,
    profile: Literal["interactive_browser", "raw_reference"] = INTERACTIVE_BROWSER_PROFILE,
) -> BrowserMeshBudgetReport:
    """Return exact post-replication budget violations without side effects."""

    if not isinstance(usage, BrowserMeshUsage):
        raise TypeError("usage must be BrowserMeshUsage.")
    resolved = BrowserMeshBudget() if budget is None else budget
    if not isinstance(resolved, BrowserMeshBudget):
        raise TypeError("budget must be BrowserMeshBudget or None.")
    resolved.validate_for_profile(profile)

    violations: list[str] = []
    if usage.final_density_face_count > resolved.max_final_density_faces:
        violations.append(
            "final_density_faces="
            f"{usage.final_density_face_count}>"
            f"{resolved.max_final_density_faces}"
        )
    if usage.final_density_vertex_count > resolved.max_final_density_vertices:
        violations.append(
            "final_density_vertices="
            f"{usage.final_density_vertex_count}>"
            f"{resolved.max_final_density_vertices}"
        )
    if usage.plotly_trace_count > resolved.max_plotly_traces:
        violations.append(
            f"plotly_traces={usage.plotly_trace_count}>{resolved.max_plotly_traces}"
        )
    if (
        usage.final_html_bytes is not None
        and usage.final_html_bytes > resolved.max_final_html_bytes
    ):
        violations.append(
            f"final_html_bytes={usage.final_html_bytes}>"
            f"{resolved.max_final_html_bytes}"
        )

    return BrowserMeshBudgetReport(
        profile=profile,
        budget=resolved,
        usage=usage,
        violations=tuple(violations),
    )


def require_browser_mesh_budget(
    usage: BrowserMeshUsage,
    *,
    budget: BrowserMeshBudget | None = None,
    profile: Literal["interactive_browser", "raw_reference"] = INTERACTIVE_BROWSER_PROFILE,
) -> BrowserMeshBudgetReport:
    """Return a passing report or raise before an oversized export is written."""

    report = evaluate_browser_mesh_budget(usage, budget=budget, profile=profile)
    if not report.passed and report.budget.hard_limit:
        raise BrowserMeshBudgetFailure(report)
    return report


def browser_usage_from_counts(
    *,
    face_counts: Sequence[int],
    vertex_counts: Sequence[int],
    trace_keys: Sequence[str] | None = None,
    display_replications: Sequence[int] | None = None,
    retained_array_bytes: Sequence[int] | None = None,
    non_density_trace_count: int = 0,
    final_html_bytes: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BrowserMeshUsage:
    """Build a usage record from aligned trace-count sequences."""

    faces = tuple(face_counts)
    vertices = tuple(vertex_counts)
    if len(faces) != len(vertices):
        raise GraphAdapterError("face_counts and vertex_counts must align.")
    count = len(faces)
    keys = (
        tuple(f"density-trace-{index}" for index in range(count))
        if trace_keys is None
        else tuple(trace_keys)
    )
    replications = (
        (1,) * count
        if display_replications is None
        else tuple(display_replications)
    )
    byte_counts = (
        (0,) * count
        if retained_array_bytes is None
        else tuple(retained_array_bytes)
    )
    if not (len(keys) == len(replications) == len(byte_counts) == count):
        raise GraphAdapterError("All per-trace browser-usage sequences must align.")
    return BrowserMeshUsage(
        density_traces=tuple(
            BrowserMeshTraceUsage(
                trace_key=str(keys[index]),
                face_count=faces[index],
                vertex_count=vertices[index],
                display_replication=replications[index],
                retained_array_bytes=byte_counts[index],
            )
            for index in range(count)
        ),
        non_density_trace_count=non_density_trace_count,
        final_html_bytes=final_html_bytes,
        metadata={} if metadata is None else metadata,
    )
