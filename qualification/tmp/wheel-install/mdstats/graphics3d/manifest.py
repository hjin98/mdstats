"""Canonical GFX3D scene-manifest evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from mdstats._version import __version__

from .contracts import GraphicsScene3DRequest
from .dependencies import GraphicsDependencyPlanEntry
from .identity import canonical_json, canonical_value, identity_digest

GRAPHICS_SCENE_MANIFEST_SCHEMA = "mdstats.graphics3d.scene-manifest.v1"


@dataclass(frozen=True, slots=True)
class GraphicsSceneManifest:
    request: GraphicsScene3DRequest
    mdstats_version: str = __version__
    source_descriptors: tuple[Mapping[str, Any], ...] = ()
    resolved_input_format: str | None = None
    atom_species_mapping: Mapping[str, Any] = field(default_factory=dict)
    frame_selection: Mapping[str, Any] = field(default_factory=dict)
    coordinate_policy: Mapping[str, Any] = field(default_factory=dict)
    display_cell_policy: Mapping[str, Any] = field(default_factory=dict)
    expanded_presets: tuple[str, ...] = ()
    dependency_plan: tuple[GraphicsDependencyPlanEntry, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_descriptors", tuple(MappingProxyType(canonical_value(value)) for value in self.source_descriptors))
        for field_name in ("atom_species_mapping", "frame_selection", "coordinate_policy", "display_cell_policy"):
            normalized = canonical_value(getattr(self, field_name))
            object.__setattr__(self, field_name, MappingProxyType(normalized))
        object.__setattr__(self, "expanded_presets", tuple(str(value) for value in self.expanded_presets))
        object.__setattr__(self, "dependency_plan", tuple(self.dependency_plan))
        object.__setattr__(self, "warnings", tuple(str(value) for value in self.warnings))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": GRAPHICS_SCENE_MANIFEST_SCHEMA,
            "mdstats_version": self.mdstats_version,
            "source_descriptors": self.source_descriptors,
            "resolved_input_format": self.resolved_input_format,
            "atom_species_mapping": self.atom_species_mapping,
            "frame_selection": self.frame_selection,
            "coordinate_policy": self.coordinate_policy,
            "display_cell_policy": self.display_cell_policy,
            "resolved_resource_request": self.request.resources,
            "ordered_layer_requests": self.request.layers,
            "scene_options": self.request.scene_options,
            "view": self.request.view,
            "output": self.request.output,
            "expanded_presets": self.expanded_presets,
            "dependency_plan": self.dependency_plan,
            "warnings": self.warnings,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_json_dict(), indent=indent)

    @property
    def manifest_id(self) -> str:
        return identity_digest(GRAPHICS_SCENE_MANIFEST_SCHEMA, self.to_json_dict())
