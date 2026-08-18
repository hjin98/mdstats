"""Immutable universal scene/layer/selection contracts for GFX3D-1."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from ase.data import atomic_numbers

from .errors import Graphics3DValidationError
from .identity import canonical_value, identity_digest

GRAPHICS_SELECTION_SCHEMA = "mdstats.graphics3d.selection.v1"
GRAPHICS_LAYER_REQUEST_SCHEMA = "mdstats.graphics3d.layer-request.v1"
GRAPHICS_SCENE_REQUEST_SCHEMA = "mdstats.graphics3d.scene-request.v1"
GRAPHICS_DEPENDENCY_KEY_SCHEMA = "mdstats.graphics3d.dependency-key.v1"
GRAPHICS_PREPARED_LAYER_SCHEMA = "mdstats.graphics3d.prepared-layer.v1"
GRAPHICS_PREPARED_SCENE_SCHEMA = "mdstats.graphics3d.prepared-scene.v1"

EntityId: TypeAlias = int | str
Pair: TypeAlias = tuple[str, str]
DependencyRole: TypeAlias = Literal["required", "optional"]


def _name(value: Any, *, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise Graphics3DValidationError(f"{field_name} must be a nonempty string.")
    return text


def _freeze_mapping(value: Mapping[str, Any] | None, *, field_name: str) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise Graphics3DValidationError(f"{field_name} must be a mapping.")
    normalized = canonical_value(value)
    assert isinstance(normalized, dict)
    return MappingProxyType(normalized)


def _entity_sort_key(value: EntityId) -> tuple[int, str]:
    return (0 if isinstance(value, int) and not isinstance(value, bool) else 1, str(value))


def _normalize_entity_ids(values: Sequence[EntityId], *, field_name: str) -> tuple[EntityId, ...]:
    normalized: list[EntityId] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, str)):
            raise Graphics3DValidationError(
                f"{field_name} values must be integer or string stable identifiers."
            )
        if isinstance(item, int):
            if item < 0:
                raise Graphics3DValidationError(f"{field_name} integer IDs must be nonnegative.")
            normalized.append(int(item))
        else:
            text = item.strip()
            if not text:
                raise Graphics3DValidationError(f"{field_name} string IDs must be nonempty.")
            normalized.append(text)
    return tuple(sorted(set(normalized), key=_entity_sort_key))


def _normalize_species(values: Sequence[str]) -> tuple[str, ...]:
    symbols: set[str] = set()
    for value in values:
        symbol = str(value).strip()
        if symbol not in atomic_numbers:
            raise Graphics3DValidationError(f"Unknown chemical species symbol {symbol!r}.")
        symbols.add(symbol)
    return tuple(sorted(symbols, key=lambda item: (int(atomic_numbers[item]), item)))


def _normalize_pairs(values: Sequence[Sequence[str]]) -> tuple[Pair, ...]:
    pairs: set[Pair] = set()
    for pair in values:
        if len(pair) != 2:
            raise Graphics3DValidationError("Each pair selection must contain exactly two species.")
        left = str(pair[0]).strip()
        right = str(pair[1]).strip()
        for symbol in (left, right):
            if symbol not in atomic_numbers:
                raise Graphics3DValidationError(f"Unknown chemical species symbol {symbol!r}.")
        ordered = tuple(sorted((left, right), key=lambda item: (int(atomic_numbers[item]), item)))
        pairs.add((ordered[0], ordered[1]))
    return tuple(sorted(pairs, key=lambda item: (atomic_numbers[item[0]], atomic_numbers[item[1]], item)))


@dataclass(frozen=True, slots=True)
class GraphicsSelection:
    """Typed universal scientific selection record.

    Layer adapters decide which fields they support.  GFX3D itself only
    normalizes and validates the common vocabulary.
    """

    species: tuple[str, ...] = ()
    atom_indices: tuple[int, ...] = ()
    atom_ids: tuple[EntityId, ...] = ()
    pairs: tuple[Pair, ...] = ()
    framework_roles: tuple[str, ...] = ()
    topology_ids: tuple[EntityId, ...] = ()
    ring_sizes: tuple[int, ...] = ()
    ring_ids: tuple[EntityId, ...] = ()
    cage_types: tuple[str, ...] = ()
    cage_ids: tuple[EntityId, ...] = ()
    site_types: tuple[str, ...] = ()
    site_ids: tuple[EntityId, ...] = ()
    state_ids: tuple[EntityId, ...] = ()
    transitions: tuple[tuple[EntityId, EntityId], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "species", _normalize_species(self.species))
        normalized_indices: list[int] = []
        for value in self.atom_indices:
            if isinstance(value, bool) or not isinstance(value, int):
                raise Graphics3DValidationError("atom_indices must contain integers.")
            if value < 0:
                raise Graphics3DValidationError("atom_indices must be nonnegative.")
            normalized_indices.append(int(value))
        object.__setattr__(self, "atom_indices", tuple(sorted(set(normalized_indices))))
        object.__setattr__(self, "atom_ids", _normalize_entity_ids(self.atom_ids, field_name="atom_ids"))
        object.__setattr__(self, "pairs", _normalize_pairs(self.pairs))
        for field_name in ("framework_roles", "cage_types", "site_types"):
            values = tuple(sorted({str(value).strip() for value in getattr(self, field_name)}))
            if any(not value for value in values):
                raise Graphics3DValidationError(f"{field_name} entries must be nonempty strings.")
            object.__setattr__(self, field_name, values)
        for field_name in ("topology_ids", "ring_ids", "cage_ids", "site_ids", "state_ids"):
            object.__setattr__(
                self,
                field_name,
                _normalize_entity_ids(getattr(self, field_name), field_name=field_name),
            )
        normalized_ring_sizes: list[int] = []
        for value in self.ring_sizes:
            if isinstance(value, bool) or not isinstance(value, int):
                raise Graphics3DValidationError("ring_sizes must contain integers >= 3.")
            if value < 3:
                raise Graphics3DValidationError("ring_sizes must contain integers >= 3.")
            normalized_ring_sizes.append(int(value))
        object.__setattr__(self, "ring_sizes", tuple(sorted(set(normalized_ring_sizes))))
        transitions: list[tuple[EntityId, EntityId]] = []
        for transition in self.transitions:
            if len(transition) != 2:
                raise Graphics3DValidationError("Each transition selection must contain source and target IDs.")
            source = _normalize_entity_ids((transition[0],), field_name="transition source")[0]
            target = _normalize_entity_ids((transition[1],), field_name="transition target")[0]
            transitions.append((source, target))
        object.__setattr__(self, "transitions", tuple(sorted(set(transitions), key=lambda x: (_entity_sort_key(x[0]), _entity_sort_key(x[1])))))

    @property
    def identity(self) -> str:
        return identity_digest(GRAPHICS_SELECTION_SCHEMA, self)

    def active_fields(self) -> frozenset[str]:
        return frozenset(
            field_name
            for field_name in self.__dataclass_fields__
            if bool(getattr(self, field_name))
        )


@dataclass(frozen=True, slots=True)
class GraphicsLayer3DRequest:
    """One named, independently configurable scene-layer request."""

    name: str
    layer_type: str
    selection: GraphicsSelection = field(default_factory=GraphicsSelection)
    analysis_options: Mapping[str, Any] = field(default_factory=dict)
    render_options: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True
    initially_visible: bool = True
    render_priority: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _name(self.name, field_name="layer name"))
        object.__setattr__(self, "layer_type", _name(self.layer_type, field_name="layer_type").lower())
        if not isinstance(self.selection, GraphicsSelection):
            raise Graphics3DValidationError("selection must be GraphicsSelection.")
        if not isinstance(self.enabled, bool) or not isinstance(self.initially_visible, bool):
            raise Graphics3DValidationError("enabled and initially_visible must be bool.")
        if isinstance(self.render_priority, bool) or not isinstance(self.render_priority, int):
            raise Graphics3DValidationError("render_priority must be an integer.")
        object.__setattr__(self, "render_priority", int(self.render_priority))
        object.__setattr__(self, "analysis_options", _freeze_mapping(self.analysis_options, field_name="analysis_options"))
        object.__setattr__(self, "render_options", _freeze_mapping(self.render_options, field_name="render_options"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, field_name="metadata"))

    @property
    def scientific_identity(self) -> str:
        return identity_digest(
            GRAPHICS_LAYER_REQUEST_SCHEMA + ".scientific",
            {
                "layer_type": self.layer_type,
                "selection": self.selection,
                "analysis_options": self.analysis_options,
            },
        )

    @property
    def render_identity(self) -> str:
        return identity_digest(
            GRAPHICS_LAYER_REQUEST_SCHEMA + ".render",
            {
                "name": self.name,
                "layer_type": self.layer_type,
                "render_options": self.render_options,
                "initially_visible": self.initially_visible,
                "enabled": self.enabled,
                "render_priority": self.render_priority,
            },
        )


@dataclass(frozen=True, slots=True)
class GraphicsScene3DRequest:
    """Normalized universal 3-D scene declaration."""

    layers: tuple[GraphicsLayer3DRequest, ...]
    scene_options: Mapping[str, Any] = field(default_factory=dict)
    view: Mapping[str, Any] = field(default_factory=dict)
    resources: Mapping[str, Any] = field(default_factory=dict)
    output: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        layers = tuple(self.layers)
        if not layers:
            raise Graphics3DValidationError("A GFX3D scene must declare at least one layer.")
        if any(not isinstance(layer, GraphicsLayer3DRequest) for layer in layers):
            raise Graphics3DValidationError("layers must contain GraphicsLayer3DRequest values.")
        names = tuple(layer.name for layer in layers)
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise Graphics3DValidationError(
                "GFX3D layer names must be unique; duplicates: " + ", ".join(duplicates)
            )
        object.__setattr__(self, "layers", layers)
        for field_name in ("scene_options", "view", "resources", "output", "metadata"):
            object.__setattr__(self, field_name, _freeze_mapping(getattr(self, field_name), field_name=field_name))

    @property
    def enabled_layers(self) -> tuple[GraphicsLayer3DRequest, ...]:
        return tuple(layer for layer in self.layers if layer.enabled)

    @property
    def scientific_identity(self) -> str:
        return identity_digest(
            GRAPHICS_SCENE_REQUEST_SCHEMA + ".scientific",
            {
                "scene_options": self.scene_options,
                "layers": [layer.scientific_identity for layer in self.enabled_layers],
            },
        )

    @property
    def render_identity(self) -> str:
        return identity_digest(
            GRAPHICS_SCENE_REQUEST_SCHEMA + ".render",
            {
                "view": self.view,
                "output": self.output,
                "layers": [layer.render_identity for layer in self.enabled_layers],
            },
        )

    @property
    def execution_request_identity(self) -> str:
        return identity_digest(
            GRAPHICS_SCENE_REQUEST_SCHEMA + ".execution-request",
            {"resources": self.resources},
        )

    @property
    def request_identity(self) -> str:
        return identity_digest(GRAPHICS_SCENE_REQUEST_SCHEMA, self)


@dataclass(frozen=True, slots=True)
class GraphicsDependencyKey:
    """Scientific cache key for a shared scene dependency."""

    provider_type: str
    scientific_options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_type", _name(self.provider_type, field_name="provider_type").lower())
        object.__setattr__(self, "scientific_options", _freeze_mapping(self.scientific_options, field_name="scientific_options"))

    @property
    def identity(self) -> str:
        return identity_digest(GRAPHICS_DEPENDENCY_KEY_SCHEMA, self)


@dataclass(frozen=True, slots=True)
class GraphicsDependencyRequest:
    key: GraphicsDependencyKey
    role: DependencyRole = "required"
    consumer_layer: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, GraphicsDependencyKey):
            raise Graphics3DValidationError("key must be GraphicsDependencyKey.")
        if self.role not in ("required", "optional"):
            raise Graphics3DValidationError("dependency role must be 'required' or 'optional'.")
        if self.consumer_layer is not None:
            object.__setattr__(self, "consumer_layer", _name(self.consumer_layer, field_name="consumer_layer"))


@dataclass(frozen=True, slots=True)
class PreparedGraphicsLayer3D:
    """Prepared scientific layer independent of renderer backend."""

    request: GraphicsLayer3DRequest
    scientific_identity: str
    primitives: tuple[Any, ...] = ()
    product_refs: Mapping[str, Any] = field(default_factory=dict, compare=False, repr=False)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    execution_evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.request, GraphicsLayer3DRequest):
            raise Graphics3DValidationError("request must be GraphicsLayer3DRequest.")
        scientific_identity = _name(self.scientific_identity, field_name="scientific_identity")
        object.__setattr__(self, "scientific_identity", scientific_identity)
        object.__setattr__(self, "primitives", tuple(self.primitives))
        # product_refs may contain opaque scientific objects; freeze the mapping shell only.
        if not isinstance(self.product_refs, Mapping):
            raise Graphics3DValidationError("product_refs must be a mapping.")
        object.__setattr__(self, "product_refs", MappingProxyType(dict(self.product_refs)))
        object.__setattr__(self, "provenance", _freeze_mapping(self.provenance, field_name="provenance"))
        object.__setattr__(self, "execution_evidence", _freeze_mapping(self.execution_evidence, field_name="execution_evidence"))

    @property
    def render_identity(self) -> str:
        return self.request.render_identity

    @property
    def execution_identity(self) -> str:
        return identity_digest(
            GRAPHICS_PREPARED_LAYER_SCHEMA + ".execution",
            {
                "layer_type": self.request.layer_type,
                "execution_evidence": self.execution_evidence,
            },
        )


@dataclass(frozen=True, slots=True)
class PreparedGraphicsScene3D:
    """Ordered collection of prepared GFX3D layers."""

    layers: tuple[PreparedGraphicsLayer3D, ...]
    manifest: Any
    display_gauge: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        layers = tuple(self.layers)
        if any(not isinstance(layer, PreparedGraphicsLayer3D) for layer in layers):
            raise Graphics3DValidationError("layers must contain PreparedGraphicsLayer3D values.")
        names = tuple(layer.request.name for layer in layers)
        if len(set(names)) != len(names):
            raise Graphics3DValidationError("Prepared GFX3D layer names must be unique.")
        object.__setattr__(self, "layers", layers)
        object.__setattr__(self, "display_gauge", _freeze_mapping(self.display_gauge, field_name="display_gauge"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, field_name="metadata"))
