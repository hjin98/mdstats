"""Dependency planning contracts for GFX3D scenes."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import GraphicsDependencyKey, GraphicsDependencyRequest


@dataclass(frozen=True, slots=True)
class GraphicsDependencyPlanEntry:
    """One deduplicated scientific dependency and its consumers."""

    key: GraphicsDependencyKey
    role: str
    consumers: tuple[str, ...]


def deduplicate_dependency_requests(
    requests: tuple[GraphicsDependencyRequest, ...] | list[GraphicsDependencyRequest],
) -> tuple[GraphicsDependencyPlanEntry, ...]:
    """Deduplicate equal scientific dependency keys in first-use order.

    If any consumer requires a key, the merged role is required. Consumer names
    are collated deterministically and do not participate in the scientific key.
    """

    grouped: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for request in requests:
        identity = request.key.identity
        if identity not in grouped:
            grouped[identity] = {
                "key": request.key,
                "required": request.role == "required",
                "consumers": set(),
            }
            order.append(identity)
        else:
            grouped[identity]["required"] = bool(grouped[identity]["required"]) or request.role == "required"
        if request.consumer_layer is not None:
            consumers = grouped[identity]["consumers"]
            assert isinstance(consumers, set)
            consumers.add(request.consumer_layer)
    entries: list[GraphicsDependencyPlanEntry] = []
    for identity in order:
        record = grouped[identity]
        consumers = record["consumers"]
        assert isinstance(consumers, set)
        entries.append(
            GraphicsDependencyPlanEntry(
                key=record["key"],  # type: ignore[arg-type]
                role="required" if bool(record["required"]) else "optional",
                consumers=tuple(sorted(str(value) for value in consumers)),
            )
        )
    return tuple(entries)
