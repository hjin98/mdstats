"""Generic layer-keyed render result contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .contracts import PreparedGraphicsScene3D
from .errors import Graphics3DValidationError
from .identity import canonical_value


@dataclass(frozen=True, slots=True)
class GraphicsLayerRenderResult:
    layer_name: str
    backend_object_indices: tuple[int, ...] = ()
    legend_group: str | None = None
    scientific_identity: str | None = None
    render_identity: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.layer_name).strip():
            raise Graphics3DValidationError("layer_name must be nonempty.")
        object.__setattr__(self, "layer_name", str(self.layer_name).strip())
        object.__setattr__(self, "backend_object_indices", tuple(int(v) for v in self.backend_object_indices))
        object.__setattr__(self, "metadata", MappingProxyType(canonical_value(self.metadata)))
        object.__setattr__(self, "warnings", tuple(str(v) for v in self.warnings))


@dataclass(frozen=True, slots=True)
class Graphics3DRenderResult:
    artifact: Any
    scene: PreparedGraphicsScene3D
    layer_results: Mapping[str, GraphicsLayerRenderResult]
    render_metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scene, PreparedGraphicsScene3D):
            raise Graphics3DValidationError("scene must be PreparedGraphicsScene3D.")
        results = dict(self.layer_results)
        expected = tuple(layer.request.name for layer in self.scene.layers)
        if tuple(results) != expected:
            raise Graphics3DValidationError(
                "layer_results must match prepared scene layer order exactly."
            )
        for name, result in results.items():
            if not isinstance(result, GraphicsLayerRenderResult) or result.layer_name != name:
                raise Graphics3DValidationError("layer_results keys must match result.layer_name.")
        object.__setattr__(self, "layer_results", MappingProxyType(results))
        object.__setattr__(self, "render_metadata", MappingProxyType(canonical_value(self.render_metadata)))
        object.__setattr__(self, "warnings", tuple(str(v) for v in self.warnings))
