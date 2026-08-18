"""Deterministic internal layer registry for GFX3D."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .contracts import (GraphicsLayer3DRequest, GraphicsDependencyRequest, GraphicsSelection, PreparedGraphicsLayer3D)
from .context import GraphicsSceneContext
from .errors import Graphics3DRegistryError, Graphics3DValidationError


@runtime_checkable
class GraphicsLayer3DAdapter(Protocol):
    """Conceptual built-in layer adapter contract."""

    def dependencies(
        self, request: GraphicsLayer3DRequest, context: GraphicsSceneContext
    ) -> tuple[GraphicsDependencyRequest, ...]: ...

    def prepare(
        self,
        request: GraphicsLayer3DRequest,
        resolved_dependencies: dict[str, Any],
        context: GraphicsSceneContext,
    ) -> PreparedGraphicsLayer3D: ...

    def render_primitives(
        self, prepared: PreparedGraphicsLayer3D, context: GraphicsSceneContext
    ) -> tuple[Any, ...]: ...


@dataclass(frozen=True, slots=True)
class GraphicsLayerRegistration:
    layer_type: str
    schema_version: str
    adapter_factory: Callable[[], GraphicsLayer3DAdapter]
    supported_selection_fields: frozenset[str] = field(default_factory=frozenset)
    scientific_option_schema: str | None = None
    render_option_schema: str | None = None
    required_dependency_providers: tuple[str, ...] = ()
    optional_dependency_providers: tuple[str, ...] = ()
    supported_primitive_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        layer_type = str(self.layer_type).strip().lower()
        if not layer_type:
            raise Graphics3DValidationError("layer_type must be nonempty.")
        schema = str(self.schema_version).strip()
        if not schema:
            raise Graphics3DValidationError("schema_version must be nonempty.")
        if not callable(self.adapter_factory):
            raise Graphics3DValidationError("adapter_factory must be callable.")
        object.__setattr__(self, "layer_type", layer_type)
        object.__setattr__(self, "schema_version", schema)
        selection_fields = frozenset(str(value).strip() for value in self.supported_selection_fields)
        valid_selection_fields = frozenset(GraphicsSelection.__dataclass_fields__)
        unknown_selection_fields = selection_fields - valid_selection_fields
        if unknown_selection_fields:
            raise Graphics3DValidationError(
                "Unknown GFX3D selection fields in registration: "
                + ", ".join(sorted(unknown_selection_fields))
            )
        object.__setattr__(self, "supported_selection_fields", selection_fields)
        object.__setattr__(
            self,
            "required_dependency_providers",
            tuple(sorted({str(value).strip().lower() for value in self.required_dependency_providers})),
        )
        object.__setattr__(
            self,
            "optional_dependency_providers",
            tuple(sorted({str(value).strip().lower() for value in self.optional_dependency_providers})),
        )
        object.__setattr__(
            self,
            "supported_primitive_types",
            tuple(sorted({str(value).strip() for value in self.supported_primitive_types})),
        )


class GraphicsLayerRegistry:
    """Internal registry with deterministic lexicographic enumeration."""

    def __init__(self) -> None:
        self._registrations: dict[str, GraphicsLayerRegistration] = {}

    def register(self, registration: GraphicsLayerRegistration) -> None:
        if not isinstance(registration, GraphicsLayerRegistration):
            raise Graphics3DRegistryError("registration must be GraphicsLayerRegistration.")
        key = registration.layer_type
        if key in self._registrations:
            raise Graphics3DRegistryError(f"GFX3D layer type {key!r} is already registered.")
        self._registrations[key] = registration

    def get(self, layer_type: str) -> GraphicsLayerRegistration:
        key = str(layer_type).strip().lower()
        try:
            return self._registrations[key]
        except KeyError as error:
            raise Graphics3DRegistryError(f"Unknown GFX3D layer type {key!r}.") from error

    def registrations(self) -> tuple[GraphicsLayerRegistration, ...]:
        return tuple(self._registrations[key] for key in sorted(self._registrations))

    def layer_types(self) -> tuple[str, ...]:
        return tuple(item.layer_type for item in self.registrations())

    def __contains__(self, layer_type: object) -> bool:
        return isinstance(layer_type, str) and layer_type.strip().lower() in self._registrations


DEFAULT_GRAPHICS_LAYER_REGISTRY = GraphicsLayerRegistry()
