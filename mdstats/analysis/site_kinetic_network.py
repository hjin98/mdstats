"""Stage-11E1 periodic structural candidate network for site microstates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from numbers import Integral
import re
from typing import Any, Mapping, Sequence

from .framework_semantics import FrameworkSemanticCatalog
from .ring_site import (
    SiteLandscapeRegime,
    SiteMicrostate,
    SiteStateKind,
    SiteTopologyInputError,
    SpeciesSiteTopologyCatalog,
)

CANONICAL_SITE_KINETIC_NETWORK_SCHEMA = "mdstats.site-kinetic-network.v1"
SITE_KINETIC_NETWORK_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class SiteKineticNetworkError(ValueError):
    """Base exception for Stage-11E1 structural networks."""


class SiteKineticNetworkInputError(SiteKineticNetworkError):
    """Raised when sources or rule values violate the contract."""


class SiteKineticNetworkInvariantError(SiteKineticNetworkError):
    """Raised when structural candidate generation is inconsistent."""


class SiteKineticNetworkResourceError(SiteKineticNetworkError):
    """Raised before declared finite-work limits are exceeded."""


class SiteKineticNetworkSerializationError(SiteKineticNetworkError):
    """Raised when canonical replay disagrees with serialized data."""


class SiteTransitionClass(str, Enum):
    INTRA_RING_CROSSING = "intra_ring_crossing"
    INTRA_RING_ANGULAR = "intra_ring_angular"
    RING_TO_CAGE = "ring_to_cage"
    INTRA_TILE_TRANSFER = "intra_tile_transfer"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise SiteKineticNetworkInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise SiteKineticNetworkInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise SiteKineticNetworkInputError(f"{name} must be positive.")
    return result


_MACHINE_LABEL = re.compile(r"^[a-z0-9][a-z0-9_.:^\-]*$")


def _machine_label(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not _MACHINE_LABEL.fullmatch(value):
        raise SiteKineticNetworkInputError(f"{name} must be a lowercase machine label.")
    return value


def _shift(value: Sequence[object], *, name: str) -> tuple[int, int, int]:
    if len(value) != 3 or any(isinstance(v, bool) or not isinstance(v, Integral) for v in value):
        raise SiteKineticNetworkInputError(f"{name} must contain three integers.")
    return tuple(int(v) for v in value)  # type: ignore[return-value]


def _sub_shift(target: Sequence[int], source: Sequence[int]) -> tuple[int, int, int]:
    return tuple(int(b) - int(a) for a, b in zip(source, target, strict=True))  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class TileTransferRule:
    tile_label: str
    interface_labels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tile_label", _machine_label(self.tile_label, name="tile_label"))
        labels = tuple(sorted(_machine_label(v, name="interface_label") for v in self.interface_labels))
        if len(labels) != len(set(labels)):
            raise SiteKineticNetworkInputError("interface_labels must be unique.")
        object.__setattr__(self, "interface_labels", labels)

    def to_dict(self) -> dict[str, Any]:
        return {"tile_label": self.tile_label, "interface_labels": list(self.interface_labels)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TileTransferRule":
        try:
            return cls(str(payload["tile_label"]), tuple(str(v) for v in payload.get("interface_labels", ())))
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteKineticNetworkSerializationError("Invalid tile-transfer rule payload.") from exc


@dataclass(frozen=True, slots=True)
class SiteKineticNetworkResources:
    max_transfer_rules: int = 256
    max_edges: int = 5_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, order=True, slots=True)
class SiteTransitionEdge:
    edge_index: int
    source_state_index: int
    target_state_index: int
    edge_class: SiteTransitionClass
    periodic_translation: tuple[int, int, int]
    pathway_label: str
    window_index: int | None = None
    mediator_tile_index: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_index", _nonnegative(self.edge_index, name="edge_index"))
        object.__setattr__(self, "source_state_index", _nonnegative(self.source_state_index, name="source_state_index"))
        object.__setattr__(self, "target_state_index", _nonnegative(self.target_state_index, name="target_state_index"))
        if self.source_state_index == self.target_state_index:
            raise SiteKineticNetworkInputError("Self-loop candidate edges are not created in Stage 11E1.")
        object.__setattr__(self, "edge_class", SiteTransitionClass(self.edge_class))
        object.__setattr__(self, "periodic_translation", _shift(self.periodic_translation, name="periodic_translation"))
        object.__setattr__(self, "pathway_label", _machine_label(self.pathway_label, name="pathway_label"))
        for name in ("window_index", "mediator_tile_index"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_index": self.edge_index, "source_state_index": self.source_state_index,
            "target_state_index": self.target_state_index, "edge_class": self.edge_class.value,
            "periodic_translation": list(self.periodic_translation), "pathway_label": self.pathway_label,
            "window_index": self.window_index, "mediator_tile_index": self.mediator_tile_index,
        }


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicSiteKineticNetwork:
    site_topology_digest: str
    framework_semantics_digest: str
    transfer_rules: tuple[TileTransferRule, ...]
    edges: tuple[SiteTransitionEdge, ...]
    canonical_schema_version: str = CANONICAL_SITE_KINETIC_NETWORK_SCHEMA
    digest_algorithm: str = SITE_KINETIC_NETWORK_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        _sha(self.site_topology_digest, name="site_topology_digest")
        _sha(self.framework_semantics_digest, name="framework_semantics_digest")
        rules = tuple(self.transfer_rules)
        edges = tuple(self.edges)
        if any(not isinstance(v, TileTransferRule) for v in rules):
            raise SiteKineticNetworkInputError("transfer_rules have the wrong type.")
        if tuple(v.edge_index for v in edges) != tuple(range(len(edges))):
            raise SiteKineticNetworkInputError("Edge IDs must be dense and ordered.")
        if self.canonical_schema_version != CANONICAL_SITE_KINETIC_NETWORK_SCHEMA or self.digest_algorithm != SITE_KINETIC_NETWORK_DIGEST_ALGORITHM:
            raise SiteKineticNetworkInputError("Unsupported site-network schema or digest algorithm.")
        object.__setattr__(self, "transfer_rules", rules)
        object.__setattr__(self, "edges", edges)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise SiteKineticNetworkInputError("Stored site-network digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PeriodicSiteKineticNetwork) and self.digest == other.digest

    def outgoing(self, state_index: int) -> tuple[SiteTransitionEdge, ...]:
        index = _nonnegative(state_index, name="state_index")
        return tuple(v for v in self.edges if v.source_state_index == index)

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "site_topology_digest": self.site_topology_digest,
            "framework_semantics_digest": self.framework_semantics_digest,
            "transfer_rules": [v.to_dict() for v in self.transfer_rules],
            "edges": [v.to_dict() for v in self.edges],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any], *, topology: SpeciesSiteTopologyCatalog,
        semantics: FrameworkSemanticCatalog, resources: SiteKineticNetworkResources | None = None,
    ) -> "PeriodicSiteKineticNetwork":
        try:
            rules = tuple(TileTransferRule.from_dict(v) for v in payload.get("transfer_rules", ()))
            rebuilt = build_site_kinetic_network(topology, semantics, transfer_rules=rules, resources=resources)
        except SiteKineticNetworkError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteKineticNetworkSerializationError("Invalid site-network payload.") from exc
        if rebuilt.to_dict() != dict(payload):
            raise SiteKineticNetworkSerializationError("Serialized site network is not canonical for the supplied sources.")
        return rebuilt


def build_site_kinetic_network(
    topology: SpeciesSiteTopologyCatalog,
    semantics: FrameworkSemanticCatalog,
    *,
    transfer_rules: Sequence[TileTransferRule] = (),
    resources: SiteKineticNetworkResources | None = None,
) -> PeriodicSiteKineticNetwork:
    """Build structural candidate pathways without assigning rates or barriers."""

    if not isinstance(topology, SpeciesSiteTopologyCatalog):
        raise SiteKineticNetworkInputError("topology must be SpeciesSiteTopologyCatalog.")
    if not isinstance(semantics, FrameworkSemanticCatalog):
        raise SiteKineticNetworkInputError("semantics must be FrameworkSemanticCatalog.")
    if topology.framework_semantics_digest != semantics.digest:
        raise SiteKineticNetworkInvariantError("The site topology and semantics do not share one source.")
    rules = tuple(transfer_rules)
    if any(not isinstance(v, TileTransferRule) for v in rules):
        raise SiteKineticNetworkInputError("transfer_rules must contain TileTransferRule records.")
    if len({v.tile_label for v in rules}) != len(rules):
        raise SiteKineticNetworkInputError("Transfer-rule tile labels must be unique.")
    active = resources or SiteKineticNetworkResources()
    if not isinstance(active, SiteKineticNetworkResources):
        raise SiteKineticNetworkInputError("resources must be SiteKineticNetworkResources.")
    if len(rules) > active.max_transfer_rules:
        raise SiteKineticNetworkResourceError("Transfer-rule count exceeds max_transfer_rules.")

    state_by_index = {v.state_index: v for v in topology.states}
    model_by_window = {v.window_index: v for v in topology.ring_models}
    cage_by_tile = {v.tile_index: v for v in topology.states if v.kind is SiteStateKind.CAGE_INTERIOR}
    rule_by_tile_label = {v.tile_label: v for v in rules}

    predicted_internal = 0
    for model in topology.ring_models:
        if not model.resolved:
            continue
        if model.regime is SiteLandscapeRegime.BILATERAL_DOUBLE_WELL:
            predicted_internal += 2
        elif model.regime is SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE:
            n_states = len(model.state_indices)
            if n_states < 2:
                raise SiteKineticNetworkInvariantError("An angular model requires at least two states.")
            predicted_internal += 2 if n_states == 2 else 2 * n_states

    predicted_ring_cage = 2 * sum(
        1
        for state in topology.states
        if state.kind is not SiteStateKind.CAGE_INTERIOR
        for exposure in state.exposures
        if exposure.tile_index in cage_by_tile
    )

    transfer_ports_by_tile: dict[int, list[tuple[SiteMicrostate, tuple[int, int, int], str]]] = {}
    predicted_transfer = 0
    for semantic_tile in semantics.tiles:
        rule = rule_by_tile_label.get(semantic_tile.effective_label)
        if rule is None:
            continue
        ports: list[tuple[SiteMicrostate, tuple[int, int, int], str]] = []
        for state in topology.states:
            if state.window_index is None or state.kind is SiteStateKind.CAGE_INTERIOR:
                continue
            interface_label = model_by_window[state.window_index].interface_label
            if rule.interface_labels and interface_label not in rule.interface_labels:
                continue
            for exposure in state.exposures:
                if exposure.tile_index == semantic_tile.tile_index:
                    ports.append((state, exposure.image_shift, interface_label))
        transfer_ports_by_tile[semantic_tile.tile_index] = ports
        predicted_transfer += 2 * sum(
            1
            for i, (first, _first_shift, _first_label) in enumerate(ports)
            for second, _second_shift, _second_label in ports[i + 1:]
            if first.state_index != second.state_index and first.window_index != second.window_index
        )

    predicted_edges = predicted_internal + predicted_ring_cage + predicted_transfer
    if predicted_edges > active.max_edges:
        raise SiteKineticNetworkResourceError(
            f"Predicted candidate edge count {predicted_edges} exceeds max_edges={active.max_edges}."
        )

    edges_raw: list[tuple[int, int, SiteTransitionClass, tuple[int, int, int], str, int | None, int | None]] = []

    def add(source: int, target: int, edge_class: SiteTransitionClass, translation: tuple[int, int, int],
            label: str, window: int | None = None, tile: int | None = None) -> None:
        edges_raw.append((source, target, edge_class, translation, label, window, tile))

    # Ring-internal candidates are dictated by the declared landscape template.
    for model in topology.ring_models:
        if not model.resolved:
            continue
        ids = model.state_indices
        if model.regime is SiteLandscapeRegime.BILATERAL_DOUBLE_WELL:
            if len(ids) != 2:
                raise SiteKineticNetworkInvariantError("A bilateral model must contain two states.")
            first, second = (state_by_index[v] for v in ids)
            shift_ab = _sub_shift(second.exposures[0].image_shift, first.exposures[0].image_shift)
            add(first.state_index, second.state_index, SiteTransitionClass.INTRA_RING_CROSSING, shift_ab,
                f"cross:w{model.window_index}:a-b", model.window_index)
            add(second.state_index, first.state_index, SiteTransitionClass.INTRA_RING_CROSSING,
                tuple(-v for v in shift_ab), f"cross:w{model.window_index}:b-a", model.window_index)
        elif model.regime is SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE:
            if len(ids) < 2:
                raise SiteKineticNetworkInvariantError("An angular model requires at least two states.")
            neighbor_pairs = sorted({tuple(sorted((ids[position], ids[(position + 1) % len(ids)]))) for position in range(len(ids))})
            for pair_index, (source, target) in enumerate(neighbor_pairs):
                add(source, target, SiteTransitionClass.INTRA_RING_ANGULAR, (0, 0, 0),
                    f"angular:w{model.window_index}:pair{pair_index}:forward", model.window_index)
                add(target, source, SiteTransitionClass.INTRA_RING_ANGULAR, (0, 0, 0),
                    f"angular:w{model.window_index}:pair{pair_index}:reverse", model.window_index)

    # Explicit cage candidates induce ring-to-cage structural paths.
    for state in topology.states:
        if state.kind is SiteStateKind.CAGE_INTERIOR:
            continue
        for exposure in state.exposures:
            cage = cage_by_tile.get(exposure.tile_index)
            if cage is None:
                continue
            cage_shift = cage.exposures[0].image_shift
            forward = _sub_shift(cage_shift, exposure.image_shift)
            anchor_token = "none" if exposure.anchor_index is None else str(exposure.anchor_index)
            label_tail = f"s{state.state_index}:t{exposure.tile_index}:a{anchor_token}:{'.'.join(map(str, exposure.image_shift))}"
            add(state.state_index, cage.state_index, SiteTransitionClass.RING_TO_CAGE, forward,
                f"ring-cage:{label_tail}", state.window_index, exposure.tile_index)
            add(cage.state_index, state.state_index, SiteTransitionClass.RING_TO_CAGE,
                tuple(-v for v in forward), f"cage-ring:{label_tail}", state.window_index, exposure.tile_index)

    # Intra-tile transfers are opt-in and are never inferred from shared incidence alone.
    for semantic_tile in semantics.tiles:
        ports = transfer_ports_by_tile.get(semantic_tile.tile_index)
        if ports is None:
            continue
        for i, (first, first_shift, _first_label) in enumerate(ports):
            for second, second_shift, _second_label in ports[i + 1:]:
                if first.state_index == second.state_index or first.window_index == second.window_index:
                    continue
                forward = _sub_shift(second_shift, first_shift)
                add(first.state_index, second.state_index, SiteTransitionClass.INTRA_TILE_TRANSFER, forward,
                    f"tile-transfer:t{semantic_tile.tile_index}:s{first.state_index}-s{second.state_index}:{'.'.join(map(str, first_shift))}:{'.'.join(map(str, second_shift))}",
                    None, semantic_tile.tile_index)
                add(second.state_index, first.state_index, SiteTransitionClass.INTRA_TILE_TRANSFER,
                    tuple(-v for v in forward),
                    f"tile-transfer:t{semantic_tile.tile_index}:s{second.state_index}-s{first.state_index}:{'.'.join(map(str, second_shift))}:{'.'.join(map(str, first_shift))}",
                    None, semantic_tile.tile_index)

    if len(edges_raw) != predicted_edges:
        raise SiteKineticNetworkInvariantError(
            f"Candidate edge preflight predicted {predicted_edges}, but construction produced {len(edges_raw)}."
        )

    # Exact duplicates are implementation errors; parallel paths with different labels/mediators remain.
    keys = [(a, b, c.value, d, e, f, g) for a, b, c, d, e, f, g in edges_raw]
    if len(keys) != len(set(keys)):
        raise SiteKineticNetworkInvariantError("Duplicate candidate edges were generated.")
    edges_raw.sort(key=lambda value: (value[0], value[1], value[2].value, value[3], value[4], -1 if value[5] is None else value[5], -1 if value[6] is None else value[6]))
    edges = tuple(
        SiteTransitionEdge(index, source, target, edge_class, translation, label, window, tile)
        for index, (source, target, edge_class, translation, label, window, tile) in enumerate(edges_raw)
    )
    return PeriodicSiteKineticNetwork(topology.digest, semantics.digest, rules, edges)


__all__ = [
    "CANONICAL_SITE_KINETIC_NETWORK_SCHEMA", "SITE_KINETIC_NETWORK_DIGEST_ALGORITHM",
    "PeriodicSiteKineticNetwork", "SiteKineticNetworkError", "SiteKineticNetworkInputError",
    "SiteKineticNetworkInvariantError", "SiteKineticNetworkResourceError",
    "SiteKineticNetworkResources", "SiteKineticNetworkSerializationError",
    "SiteTransitionClass", "SiteTransitionEdge", "TileTransferRule", "build_site_kinetic_network",
]
