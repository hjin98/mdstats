"""Compositional material-profile and atom-group contracts for MLFF workflows.

This module owns declarative identity only.  It does not calculate structural
features, infer a material type, or import material-specific implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Mapping, Protocol, runtime_checkable

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    tuple_value,
    validate_digest,
)

MATERIAL_PROFILE_PROVIDER_IDENTITY_SCHEMA = "mdstats.material-profile-provider-identity.v1"
PHASE_COMPONENT_IDENTITY_SCHEMA = "mdstats.phase-component-identity.v1"
MATERIAL_PROFILE_IDENTITY_SCHEMA = "mdstats.material-profile-identity.v1"
ATOM_GROUP_SELECTOR_SCHEMA = "mdstats.atom-group-selector.v1"
ATOM_GROUP_DEFINITION_SCHEMA = "mdstats.atom-group-definition.v1"
ATOM_GROUP_CATALOG_SCHEMA = "mdstats.atom-group-catalog.v1"
CONDITION_AXIS_DEFINITION_SCHEMA = "mdstats.condition-axis-definition.v1"
CONDITION_AXIS_CATALOG_SCHEMA = "mdstats.condition-axis-catalog.v1"
INDEPENDENCE_AXIS_DEFINITION_SCHEMA = "mdstats.independence-axis-definition.v1"
INDEPENDENCE_AXIS_CATALOG_SCHEMA = "mdstats.independence-axis-catalog.v1"
MATERIAL_PROFILE_CONTRACTS_SCHEMA = "mdstats.material-profile-contracts.v1"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")


def _identifier(value: str, *, name: str) -> str:
    result = str(value).strip()
    if not _IDENTIFIER_RE.fullmatch(result):
        raise TrainingDataInputError(
            f"{name} must begin with a letter and contain only letters, digits, '.', '_', ':', or '-'."
        )
    return result


def _nonempty_text(value: str, *, name: str) -> str:
    result = str(value).strip()
    if not result:
        raise TrainingDataInputError(f"{name} must be non-empty.")
    return result


def _unique_tokens(values: tuple[str, ...] | list[str], *, name: str) -> tuple[str, ...]:
    original = tuple(values)
    normalized = tuple(_identifier(value, name=name) for value in original)
    if len(set(normalized)) != len(normalized):
        raise TrainingDataInputError(f"{name} entries must be unique.")
    return tuple(sorted(normalized))






def _strict_integer_tuple(values: tuple[int, ...], *, name: str, minimum: int) -> tuple[int, ...]:
    result: list[int] = []
    for value in values:
        if isinstance(value, bool):
            raise TrainingDataInputError(f"{name} entries must be integers, not booleans.")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric != int(numeric):
            raise TrainingDataInputError(f"{name} entries must be finite integers.")
        integer = int(numeric)
        if integer < minimum:
            relation = "positive" if minimum == 1 else "nonnegative"
            raise TrainingDataInputError(f"{name} entries must be {relation} integers.")
        result.append(integer)
    if len(set(result)) != len(result):
        raise TrainingDataInputError(f"{name} entries must be unique.")
    return tuple(sorted(result))

def _frozen_json_mapping(value: Mapping[str, Any] | tuple[tuple[str, Any], ...]) -> tuple[tuple[str, Any], ...]:
    if isinstance(value, Mapping):
        frozen = tuple_value(json_value(value))
    elif isinstance(value, tuple):
        frozen = tuple_value(json_value(_thaw_json(value)))
    else:
        raise TrainingDataInputError("provider_parameters must be a mapping.")
    if not isinstance(frozen, tuple) or any(not isinstance(item, tuple) or len(item) != 2 for item in frozen):
        raise TrainingDataInputError("provider_parameters must be a string-keyed mapping.")
    return frozen


def _thaw_json(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {item[0]: _thaw_json(item[1]) for item in value}
        return [_thaw_json(item) for item in value]
    return value

def _enum_or_identifier(value: str | Enum, enum_type: type[Enum], *, name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value)
    try:
        return str(enum_type(raw).value)
    except ValueError:
        return _identifier(raw, name=name)


class MaterialPhaseKind(str, Enum):
    CRYSTALLINE_SOLID = "crystalline_solid"
    AMORPHOUS_SOLID = "amorphous_solid"
    LIQUID = "liquid"
    MOLECULAR_OR_GAS = "molecular_or_gas"
    OTHER = "other"


class MaterialGeometryKind(str, Enum):
    BULK = "bulk"
    SURFACE = "surface"
    INTERFACE = "interface"
    CONFINED = "confined"
    CLUSTER = "cluster"
    OTHER = "other"


class ChemistryModifier(str, Enum):
    METALLIC = "metallic"
    IONIC = "ionic"
    COVALENT_NETWORK = "covalent_network"
    MOLECULAR = "molecular"
    REACTIVE = "reactive"
    MAGNETIC = "magnetic"
    CHARGED_OR_POLAR = "charged_or_polar"
    MIXED_BONDING = "mixed_bonding"


class StructuralExtension(str, Enum):
    POROUS_NETWORK = "porous_network"
    ZEOLITE = "zeolite"
    LTA = "lta"
    LAYERED = "layered"
    POLYMER = "polymer"
    GRAIN_BOUNDARY = "grain_boundary"
    DEFECTIVE_CRYSTAL = "defective_crystal"


class AtomGroupSelectorKind(str, Enum):
    ALL_ATOMS = "all_atoms"
    ATOMIC_NUMBERS = "atomic_numbers"
    ATOM_INDICES = "atom_indices"
    METADATA_VALUE = "metadata_value"
    PROVIDER = "provider"
    COMPOSITE = "composite"


class AtomGroupScope(str, Enum):
    STATIC_TOPOLOGY = "static_topology"
    FRAME_DYNAMIC = "frame_dynamic"


class AtomGroupSetOperation(str, Enum):
    UNION = "union"
    INTERSECTION = "intersection"
    DIFFERENCE = "difference"
    COMPLEMENT = "complement"


class AxisValueKind(str, Enum):
    CATEGORICAL = "categorical"
    CONTINUOUS = "continuous"
    INTEGER = "integer"
    BOOLEAN = "boolean"


class ConditionAxisRole(str, Enum):
    COVERAGE = "coverage"
    STRATIFICATION = "stratification"
    CHALLENGE = "challenge"
    REPORTING = "reporting"


class IndependenceAxisScope(str, Enum):
    SOURCE = "source"
    INITIAL_CONFIGURATION = "initial_configuration"
    TRAJECTORY = "trajectory"
    REPLICA = "replica"
    STRUCTURAL_REALIZATION = "structural_realization"
    THERMODYNAMIC_SEED = "thermodynamic_seed"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class MaterialProfileProviderIdentity:
    provider_id: str
    provider_version: str
    configuration_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _identifier(self.provider_id, name="provider_id"))
        object.__setattr__(self, "provider_version", _nonempty_text(self.provider_version, name="provider_version"))
        object.__setattr__(
            self,
            "configuration_digest",
            validate_digest(self.configuration_digest, name="configuration_digest"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MATERIAL_PROFILE_PROVIDER_IDENTITY_SCHEMA,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "configuration_digest": self.configuration_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_configuration(
        cls,
        *,
        provider_id: str,
        provider_version: str,
        configuration: Mapping[str, Any],
    ) -> "MaterialProfileProviderIdentity":
        return cls(
            provider_id=provider_id,
            provider_version=provider_version,
            configuration_digest=digest(configuration),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaterialProfileProviderIdentity":
        if payload.get("schema") != MATERIAL_PROFILE_PROVIDER_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported material-profile-provider schema.")
        result = cls(
            provider_id=str(payload["provider_id"]),
            provider_version=str(payload["provider_version"]),
            configuration_digest=str(payload["configuration_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Material-profile-provider digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PhaseComponentIdentity:
    phase_id: str
    phase_kind: MaterialPhaseKind
    atom_group_ids: tuple[str, ...]
    chemistry_modifiers: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase_id", _identifier(self.phase_id, name="phase_id"))
        object.__setattr__(self, "phase_kind", MaterialPhaseKind(self.phase_kind))
        groups = _unique_tokens(self.atom_group_ids, name="atom_group_id")
        if not groups:
            raise TrainingDataInputError("Every phase must declare at least one atom group.")
        object.__setattr__(self, "atom_group_ids", groups)
        modifiers = tuple(sorted({_enum_or_identifier(value, ChemistryModifier, name="chemistry_modifier") for value in self.chemistry_modifiers}))
        if len(modifiers) != len(self.chemistry_modifiers):
            raise TrainingDataInputError("Phase chemistry modifiers must be unique.")
        object.__setattr__(self, "chemistry_modifiers", modifiers)
        object.__setattr__(self, "notes", tuple(_nonempty_text(v, name="phase note") for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PHASE_COMPONENT_IDENTITY_SCHEMA,
            "phase_id": self.phase_id,
            "phase_kind": self.phase_kind.value,
            "atom_group_ids": list(self.atom_group_ids),
            "chemistry_modifiers": list(self.chemistry_modifiers),
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PhaseComponentIdentity":
        if payload.get("schema") != PHASE_COMPONENT_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported phase-component schema.")
        result = cls(
            phase_id=str(payload["phase_id"]),
            phase_kind=MaterialPhaseKind(str(payload["phase_kind"])),
            atom_group_ids=tuple(str(v) for v in payload.get("atom_group_ids", ())),
            chemistry_modifiers=tuple(str(v) for v in payload.get("chemistry_modifiers", ())),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Phase-component digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaterialProfileIdentity:
    profile_id: str
    profile_version: str
    phases: tuple[PhaseComponentIdentity, ...]
    geometry: MaterialGeometryKind = MaterialGeometryKind.BULK
    chemistry_modifiers: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()
    provider_identity: MaterialProfileProviderIdentity | None = None
    user_declared: bool = True
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _identifier(self.profile_id, name="profile_id"))
        object.__setattr__(self, "profile_version", _nonempty_text(self.profile_version, name="profile_version"))
        phases = tuple(sorted(self.phases, key=lambda item: item.phase_id))
        if not phases or len({item.phase_id for item in phases}) != len(phases):
            raise TrainingDataInputError("Material profiles require one or more uniquely named phases.")
        object.__setattr__(self, "phases", phases)
        object.__setattr__(self, "geometry", MaterialGeometryKind(self.geometry))
        if self.geometry is MaterialGeometryKind.INTERFACE and len(phases) < 2:
            raise TrainingDataInputError("An interface profile must declare at least two phases.")
        modifiers = tuple(sorted({_enum_or_identifier(value, ChemistryModifier, name="chemistry_modifier") for value in self.chemistry_modifiers}))
        if len(modifiers) != len(self.chemistry_modifiers):
            raise TrainingDataInputError("Material chemistry modifiers must be unique.")
        object.__setattr__(self, "chemistry_modifiers", modifiers)
        extensions = tuple(sorted({_enum_or_identifier(value, StructuralExtension, name="structural_extension") for value in self.extensions}))
        if len(extensions) != len(self.extensions):
            raise TrainingDataInputError("Structural extensions must be unique.")
        if StructuralExtension.LTA.value in extensions and StructuralExtension.ZEOLITE.value not in extensions:
            raise TrainingDataInputError("The LTA extension requires the zeolite extension.")
        if StructuralExtension.ZEOLITE.value in extensions and StructuralExtension.POROUS_NETWORK.value not in extensions:
            raise TrainingDataInputError("The zeolite extension requires the porous_network extension.")
        object.__setattr__(self, "extensions", extensions)
        if not self.user_declared:
            raise TrainingDataInputError(
                "DATA9A7a production profiles must be explicitly user-declared; advisory inference cannot become identity evidence."
            )
        object.__setattr__(self, "notes", tuple(_nonempty_text(v, name="profile note") for v in self.notes))

    @property
    def phase_ids(self) -> tuple[str, ...]:
        return tuple(item.phase_id for item in self.phases)

    @property
    def atom_group_ids(self) -> tuple[str, ...]:
        return tuple(sorted({group for phase in self.phases for group in phase.atom_group_ids}))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MATERIAL_PROFILE_IDENTITY_SCHEMA,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "phases": [item.to_dict() for item in self.phases],
            "geometry": self.geometry.value,
            "chemistry_modifiers": list(self.chemistry_modifiers),
            "extensions": list(self.extensions),
            "provider_identity": None if self.provider_identity is None else self.provider_identity.to_dict(),
            "user_declared": self.user_declared,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaterialProfileIdentity":
        if payload.get("schema") != MATERIAL_PROFILE_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported material-profile schema.")
        result = cls(
            profile_id=str(payload["profile_id"]),
            profile_version=str(payload["profile_version"]),
            phases=tuple(PhaseComponentIdentity.from_dict(v) for v in payload.get("phases", ())),
            geometry=MaterialGeometryKind(str(payload["geometry"])),
            chemistry_modifiers=tuple(str(v) for v in payload.get("chemistry_modifiers", ())),
            extensions=tuple(str(v) for v in payload.get("extensions", ())),
            provider_identity=None if payload.get("provider_identity") is None else MaterialProfileProviderIdentity.from_dict(payload["provider_identity"]),
            user_declared=bool(payload.get("user_declared", True)),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Material-profile digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AtomGroupSelector:
    kind: AtomGroupSelectorKind
    atomic_numbers: tuple[int, ...] = ()
    atom_indices: tuple[int, ...] = ()
    metadata_key: str | None = None
    metadata_values: tuple[str, ...] = ()
    provider_identity: MaterialProfileProviderIdentity | None = None
    source_group_ids: tuple[str, ...] = ()
    operation: AtomGroupSetOperation | None = None
    provider_parameters: Mapping[str, Any] | tuple[tuple[str, Any], ...] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", AtomGroupSelectorKind(self.kind))
        numbers = _strict_integer_tuple(self.atomic_numbers, name="atomic_numbers", minimum=1)
        indices = _strict_integer_tuple(self.atom_indices, name="atom_indices", minimum=0)
        metadata_values = tuple(sorted(set(str(v) for v in self.metadata_values)))
        normalized_source_groups = tuple(_identifier(v, name="source_group_id") for v in self.source_group_ids)
        if len(set(normalized_source_groups)) != len(normalized_source_groups):
            raise TrainingDataInputError("source_group_ids must be unique.")
        source_groups = normalized_source_groups
        object.__setattr__(self, "atomic_numbers", numbers)
        object.__setattr__(self, "atom_indices", indices)
        object.__setattr__(self, "metadata_values", metadata_values)
        object.__setattr__(self, "source_group_ids", source_groups)
        object.__setattr__(self, "provider_parameters", _frozen_json_mapping(self.provider_parameters))
        if self.operation is not None:
            object.__setattr__(self, "operation", AtomGroupSetOperation(self.operation))

        if self.kind is AtomGroupSelectorKind.ALL_ATOMS:
            if any((numbers, indices, self.metadata_key, metadata_values, self.provider_identity, source_groups, self.operation, self.provider_parameters)):
                raise TrainingDataInputError("all_atoms selectors cannot carry selector-specific fields.")
        elif self.kind is AtomGroupSelectorKind.ATOMIC_NUMBERS:
            if not numbers or any((indices, self.metadata_key, metadata_values, self.provider_identity, source_groups, self.operation, self.provider_parameters)):
                raise TrainingDataInputError("atomic_numbers selectors require only atomic_numbers.")
        elif self.kind is AtomGroupSelectorKind.ATOM_INDICES:
            if not indices or any((numbers, self.metadata_key, metadata_values, self.provider_identity, source_groups, self.operation, self.provider_parameters)):
                raise TrainingDataInputError("atom_indices selectors require only atom_indices.")
        elif self.kind is AtomGroupSelectorKind.METADATA_VALUE:
            if not self.metadata_key or not metadata_values or any((numbers, indices, self.provider_identity, source_groups, self.operation, self.provider_parameters)):
                raise TrainingDataInputError("metadata_value selectors require metadata_key and metadata_values only.")
            object.__setattr__(self, "metadata_key", _identifier(self.metadata_key, name="metadata_key"))
        elif self.kind is AtomGroupSelectorKind.PROVIDER:
            if self.provider_identity is None or any((numbers, indices, self.metadata_key, metadata_values, source_groups, self.operation)):
                raise TrainingDataInputError("provider selectors require provider_identity and optional provider_parameters only.")
        elif self.kind is AtomGroupSelectorKind.COMPOSITE:
            if not source_groups or self.operation is None or any((numbers, indices, self.metadata_key, metadata_values, self.provider_identity, self.provider_parameters)):
                raise TrainingDataInputError("composite selectors require source_group_ids and operation only.")
            if self.operation is AtomGroupSetOperation.COMPLEMENT and len(source_groups) != 1:
                raise TrainingDataInputError("complement selectors require exactly one source group.")
            if self.operation in {AtomGroupSetOperation.UNION, AtomGroupSetOperation.INTERSECTION, AtomGroupSetOperation.DIFFERENCE} and len(source_groups) < 2:
                raise TrainingDataInputError(f"{self.operation.value} selectors require at least two source groups.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOM_GROUP_SELECTOR_SCHEMA,
            "kind": self.kind.value,
            "atomic_numbers": list(self.atomic_numbers),
            "atom_indices": list(self.atom_indices),
            "metadata_key": self.metadata_key,
            "metadata_values": list(self.metadata_values),
            "provider_identity": None if self.provider_identity is None else self.provider_identity.to_dict(),
            "source_group_ids": list(self.source_group_ids),
            "operation": None if self.operation is None else self.operation.value,
            "provider_parameters": _thaw_json(self.provider_parameters),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomGroupSelector":
        if payload.get("schema") != ATOM_GROUP_SELECTOR_SCHEMA:
            raise TrainingDataSerializationError("Unsupported atom-group-selector schema.")
        result = cls(
            kind=AtomGroupSelectorKind(str(payload["kind"])),
            atomic_numbers=tuple(int(v) for v in payload.get("atomic_numbers", ())),
            atom_indices=tuple(int(v) for v in payload.get("atom_indices", ())),
            metadata_key=None if payload.get("metadata_key") is None else str(payload["metadata_key"]),
            metadata_values=tuple(str(v) for v in payload.get("metadata_values", ())),
            provider_identity=None if payload.get("provider_identity") is None else MaterialProfileProviderIdentity.from_dict(payload["provider_identity"]),
            source_group_ids=tuple(str(v) for v in payload.get("source_group_ids", ())),
            operation=None if payload.get("operation") is None else AtomGroupSetOperation(str(payload["operation"])),
            provider_parameters=payload.get("provider_parameters", {}),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Atom-group-selector digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AtomGroupDefinition:
    group_id: str
    label: str
    selector: AtomGroupSelector
    scope: AtomGroupScope = AtomGroupScope.STATIC_TOPOLOGY
    phase_ids: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    allow_empty: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "group_id", _identifier(self.group_id, name="group_id"))
        object.__setattr__(self, "label", _nonempty_text(self.label, name="atom-group label"))
        object.__setattr__(self, "scope", AtomGroupScope(self.scope))
        phases = _unique_tokens(self.phase_ids, name="phase_id") if self.phase_ids else ()
        roles = _unique_tokens(self.roles, name="atom-group role") if self.roles else ()
        object.__setattr__(self, "phase_ids", phases)
        object.__setattr__(self, "roles", roles)
        object.__setattr__(self, "notes", tuple(_nonempty_text(v, name="atom-group note") for v in self.notes))
        if self.selector.kind is AtomGroupSelectorKind.PROVIDER and self.scope is not AtomGroupScope.FRAME_DYNAMIC:
            raise TrainingDataInputError("Provider-defined atom groups must declare frame_dynamic scope.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOM_GROUP_DEFINITION_SCHEMA,
            "group_id": self.group_id,
            "label": self.label,
            "selector": self.selector.to_dict(),
            "scope": self.scope.value,
            "phase_ids": list(self.phase_ids),
            "roles": list(self.roles),
            "allow_empty": self.allow_empty,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomGroupDefinition":
        if payload.get("schema") != ATOM_GROUP_DEFINITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported atom-group-definition schema.")
        result = cls(
            group_id=str(payload["group_id"]),
            label=str(payload["label"]),
            selector=AtomGroupSelector.from_dict(payload["selector"]),
            scope=AtomGroupScope(str(payload["scope"])),
            phase_ids=tuple(str(v) for v in payload.get("phase_ids", ())),
            roles=tuple(str(v) for v in payload.get("roles", ())),
            allow_empty=bool(payload.get("allow_empty", False)),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Atom-group-definition digest mismatch.")
        return result


def _assert_composite_group_dag(groups: tuple[AtomGroupDefinition, ...]) -> None:
    group_ids = {group.group_id for group in groups}
    dependencies = {
        group.group_id: set(group.selector.source_group_ids)
        for group in groups
        if group.selector.kind is AtomGroupSelectorKind.COMPOSITE
    }
    for group_id, refs in dependencies.items():
        if group_id in refs:
            raise TrainingDataInputError("Composite atom groups cannot reference themselves.")
        unknown = refs - group_ids
        if unknown:
            raise TrainingDataInputError(f"Composite atom group {group_id!r} references unknown groups {sorted(unknown)!r}.")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(group_id: str) -> None:
        if group_id in visited:
            return
        if group_id in visiting:
            raise TrainingDataInputError("Composite atom-group dependencies contain a cycle.")
        visiting.add(group_id)
        for dependency in dependencies.get(group_id, ()):
            visit(dependency)
        visiting.remove(group_id)
        visited.add(group_id)

    for group_id in group_ids:
        visit(group_id)


@dataclass(frozen=True, slots=True)
class AtomGroupCatalog:
    material_profile_digest: str
    material_phase_ids: tuple[str, ...]
    groups: tuple[AtomGroupDefinition, ...]
    catalog_id: str = "default_atom_groups"
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_profile_digest", validate_digest(self.material_profile_digest, name="material_profile_digest"))
        object.__setattr__(self, "catalog_id", _identifier(self.catalog_id, name="catalog_id"))
        phases = _unique_tokens(self.material_phase_ids, name="phase_id")
        if not phases:
            raise TrainingDataInputError("Atom-group catalogs require material phase IDs.")
        object.__setattr__(self, "material_phase_ids", phases)
        groups = tuple(sorted(self.groups, key=lambda item: item.group_id))
        if not groups or len({item.group_id for item in groups}) != len(groups):
            raise TrainingDataInputError("Atom-group catalogs require uniquely named groups.")
        phase_set = set(phases)
        for group in groups:
            unknown = set(group.phase_ids) - phase_set
            if unknown:
                raise TrainingDataInputError(f"Atom group {group.group_id!r} references unknown phases {sorted(unknown)!r}.")
        _assert_composite_group_dag(groups)
        object.__setattr__(self, "groups", groups)
        object.__setattr__(self, "notes", tuple(_nonempty_text(v, name="catalog note") for v in self.notes))

    @property
    def group_ids(self) -> tuple[str, ...]:
        return tuple(item.group_id for item in self.groups)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOM_GROUP_CATALOG_SCHEMA,
            "material_profile_digest": self.material_profile_digest,
            "material_phase_ids": list(self.material_phase_ids),
            "groups": [item.to_dict() for item in self.groups],
            "catalog_id": self.catalog_id,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomGroupCatalog":
        if payload.get("schema") != ATOM_GROUP_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported atom-group-catalog schema.")
        result = cls(
            material_profile_digest=str(payload["material_profile_digest"]),
            material_phase_ids=tuple(str(v) for v in payload.get("material_phase_ids", ())),
            groups=tuple(AtomGroupDefinition.from_dict(v) for v in payload.get("groups", ())),
            catalog_id=str(payload.get("catalog_id", "default_atom_groups")),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Atom-group-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ConditionAxisDefinition:
    axis_id: str
    label: str
    value_kind: AxisValueKind
    roles: tuple[ConditionAxisRole, ...] = (ConditionAxisRole.COVERAGE,)
    unit: str | None = None
    required: bool = False
    allowed_values: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis_id", _identifier(self.axis_id, name="condition axis_id"))
        object.__setattr__(self, "label", _nonempty_text(self.label, name="condition-axis label"))
        object.__setattr__(self, "value_kind", AxisValueKind(self.value_kind))
        roles = tuple(sorted({ConditionAxisRole(v) for v in self.roles}, key=lambda item: item.value))
        if not roles or len(roles) != len(self.roles):
            raise TrainingDataInputError("Condition-axis roles must be non-empty and unique.")
        object.__setattr__(self, "roles", roles)
        if self.unit is not None:
            object.__setattr__(self, "unit", _nonempty_text(self.unit, name="condition-axis unit"))
        normalized_values = tuple(_nonempty_text(v, name="condition-axis allowed value") for v in self.allowed_values)
        if len(set(normalized_values)) != len(normalized_values):
            raise TrainingDataInputError("Condition-axis allowed values must be unique.")
        values = tuple(sorted(normalized_values))
        object.__setattr__(self, "allowed_values", values)
        if self.value_kind in {AxisValueKind.CATEGORICAL, AxisValueKind.BOOLEAN}:
            if self.minimum is not None or self.maximum is not None:
                raise TrainingDataInputError("Categorical/boolean axes cannot define numeric bounds.")
            if self.value_kind is AxisValueKind.BOOLEAN and values:
                raise TrainingDataInputError("Boolean axes do not need allowed_values.")
        else:
            if values:
                raise TrainingDataInputError("Continuous/integer axes cannot define allowed_values.")
            for name, bound in (("minimum", self.minimum), ("maximum", self.maximum)):
                if bound is not None and not math.isfinite(float(bound)):
                    raise TrainingDataInputError(f"Condition-axis {name} must be finite.")
                if bound is not None and self.value_kind is AxisValueKind.INTEGER and float(bound) != int(float(bound)):
                    raise TrainingDataInputError(f"Integer condition-axis {name} must be integral.")
            if self.minimum is not None and self.maximum is not None and float(self.minimum) > float(self.maximum):
                raise TrainingDataInputError("Condition-axis minimum cannot exceed maximum.")
        object.__setattr__(self, "notes", tuple(_nonempty_text(v, name="condition-axis note") for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CONDITION_AXIS_DEFINITION_SCHEMA,
            "axis_id": self.axis_id,
            "label": self.label,
            "value_kind": self.value_kind.value,
            "roles": [item.value for item in self.roles],
            "unit": self.unit,
            "required": self.required,
            "allowed_values": list(self.allowed_values),
            "minimum": self.minimum,
            "maximum": self.maximum,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConditionAxisDefinition":
        if payload.get("schema") != CONDITION_AXIS_DEFINITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported condition-axis-definition schema.")
        result = cls(
            axis_id=str(payload["axis_id"]),
            label=str(payload["label"]),
            value_kind=AxisValueKind(str(payload["value_kind"])),
            roles=tuple(ConditionAxisRole(str(v)) for v in payload.get("roles", (ConditionAxisRole.COVERAGE.value,))),
            unit=None if payload.get("unit") is None else str(payload["unit"]),
            required=bool(payload.get("required", False)),
            allowed_values=tuple(str(v) for v in payload.get("allowed_values", ())),
            minimum=None if payload.get("minimum") is None else float(payload["minimum"]),
            maximum=None if payload.get("maximum") is None else float(payload["maximum"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Condition-axis-definition digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ConditionAxisCatalog:
    material_profile_digest: str
    axes: tuple[ConditionAxisDefinition, ...]
    catalog_id: str = "default_condition_axes"

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_profile_digest", validate_digest(self.material_profile_digest, name="material_profile_digest"))
        object.__setattr__(self, "catalog_id", _identifier(self.catalog_id, name="catalog_id"))
        axes = tuple(sorted(self.axes, key=lambda item: item.axis_id))
        if len({item.axis_id for item in axes}) != len(axes):
            raise TrainingDataInputError("Condition-axis IDs must be unique.")
        object.__setattr__(self, "axes", axes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CONDITION_AXIS_CATALOG_SCHEMA,
            "material_profile_digest": self.material_profile_digest,
            "axes": [item.to_dict() for item in self.axes],
            "catalog_id": self.catalog_id,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConditionAxisCatalog":
        if payload.get("schema") != CONDITION_AXIS_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported condition-axis-catalog schema.")
        result = cls(
            material_profile_digest=str(payload["material_profile_digest"]),
            axes=tuple(ConditionAxisDefinition.from_dict(v) for v in payload.get("axes", ())),
            catalog_id=str(payload.get("catalog_id", "default_condition_axes")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Condition-axis-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class IndependenceAxisDefinition:
    axis_id: str
    label: str
    scope: IndependenceAxisScope
    required_for_roles: tuple[str, ...] = ()
    minimum_distinct_values: int = 2
    leakage_barrier: bool = True
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis_id", _identifier(self.axis_id, name="independence axis_id"))
        object.__setattr__(self, "label", _nonempty_text(self.label, name="independence-axis label"))
        object.__setattr__(self, "scope", IndependenceAxisScope(self.scope))
        roles = _unique_tokens(self.required_for_roles, name="statistical role") if self.required_for_roles else ()
        object.__setattr__(self, "required_for_roles", roles)
        if isinstance(self.minimum_distinct_values, bool):
            raise TrainingDataInputError("minimum_distinct_values must be an integer.")
        distinct = float(self.minimum_distinct_values)
        if not math.isfinite(distinct) or distinct != int(distinct) or int(distinct) < 1:
            raise TrainingDataInputError("minimum_distinct_values must be a positive integer.")
        object.__setattr__(self, "minimum_distinct_values", int(distinct))
        object.__setattr__(self, "notes", tuple(_nonempty_text(v, name="independence-axis note") for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": INDEPENDENCE_AXIS_DEFINITION_SCHEMA,
            "axis_id": self.axis_id,
            "label": self.label,
            "scope": self.scope.value,
            "required_for_roles": list(self.required_for_roles),
            "minimum_distinct_values": self.minimum_distinct_values,
            "leakage_barrier": self.leakage_barrier,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IndependenceAxisDefinition":
        if payload.get("schema") != INDEPENDENCE_AXIS_DEFINITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported independence-axis-definition schema.")
        result = cls(
            axis_id=str(payload["axis_id"]),
            label=str(payload["label"]),
            scope=IndependenceAxisScope(str(payload["scope"])),
            required_for_roles=tuple(str(v) for v in payload.get("required_for_roles", ())),
            minimum_distinct_values=int(payload.get("minimum_distinct_values", 2)),
            leakage_barrier=bool(payload.get("leakage_barrier", True)),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Independence-axis-definition digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class IndependenceAxisCatalog:
    material_profile_digest: str
    axes: tuple[IndependenceAxisDefinition, ...]
    catalog_id: str = "default_independence_axes"

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_profile_digest", validate_digest(self.material_profile_digest, name="material_profile_digest"))
        object.__setattr__(self, "catalog_id", _identifier(self.catalog_id, name="catalog_id"))
        axes = tuple(sorted(self.axes, key=lambda item: item.axis_id))
        if len({item.axis_id for item in axes}) != len(axes):
            raise TrainingDataInputError("Independence-axis IDs must be unique.")
        object.__setattr__(self, "axes", axes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": INDEPENDENCE_AXIS_CATALOG_SCHEMA,
            "material_profile_digest": self.material_profile_digest,
            "axes": [item.to_dict() for item in self.axes],
            "catalog_id": self.catalog_id,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IndependenceAxisCatalog":
        if payload.get("schema") != INDEPENDENCE_AXIS_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported independence-axis-catalog schema.")
        result = cls(
            material_profile_digest=str(payload["material_profile_digest"]),
            axes=tuple(IndependenceAxisDefinition.from_dict(v) for v in payload.get("axes", ())),
            catalog_id=str(payload.get("catalog_id", "default_independence_axes")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Independence-axis-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaterialProfileContracts:
    profile: MaterialProfileIdentity
    atom_groups: AtomGroupCatalog
    condition_axes: ConditionAxisCatalog
    independence_axes: IndependenceAxisCatalog
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        profile_digest = self.profile.content_digest
        for name, value in (
            ("atom_groups", self.atom_groups.material_profile_digest),
            ("condition_axes", self.condition_axes.material_profile_digest),
            ("independence_axes", self.independence_axes.material_profile_digest),
        ):
            if value != profile_digest:
                raise TrainingDataInputError(f"{name} does not belong to the material profile.")
        if self.atom_groups.material_phase_ids != self.profile.phase_ids:
            raise TrainingDataInputError("Atom-group catalog phase IDs do not match the material profile.")
        missing_groups = set(self.profile.atom_group_ids) - set(self.atom_groups.group_ids)
        if missing_groups:
            raise TrainingDataInputError(f"Material profile references missing atom groups {sorted(missing_groups)!r}.")
        group_by_id = {group.group_id: group for group in self.atom_groups.groups}
        for phase in self.profile.phases:
            for group_id in phase.atom_group_ids:
                if phase.phase_id not in group_by_id[group_id].phase_ids:
                    raise TrainingDataInputError(
                        f"Phase {phase.phase_id!r} references atom group {group_id!r}, but that group is not assigned to the phase."
                    )
        object.__setattr__(self, "notes", tuple(_nonempty_text(v, name="contract note") for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MATERIAL_PROFILE_CONTRACTS_SCHEMA,
            "profile": self.profile.to_dict(),
            "atom_groups": self.atom_groups.to_dict(),
            "condition_axes": self.condition_axes.to_dict(),
            "independence_axes": self.independence_axes.to_dict(),
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaterialProfileContracts":
        if payload.get("schema") != MATERIAL_PROFILE_CONTRACTS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported material-profile-contracts schema.")
        result = cls(
            profile=MaterialProfileIdentity.from_dict(payload["profile"]),
            atom_groups=AtomGroupCatalog.from_dict(payload["atom_groups"]),
            condition_axes=ConditionAxisCatalog.from_dict(payload["condition_axes"]),
            independence_axes=IndependenceAxisCatalog.from_dict(payload["independence_axes"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Material-profile-contracts digest mismatch.")
        return result


@runtime_checkable
class SystemProfileProvider(Protocol):
    """Provider boundary for declarative DATA9A7a contracts only.

    Scientific feature, event, and selection providers are introduced in later
    DATA9A7 stages and are intentionally not part of this first protocol.
    """

    provider_id: str
    provider_version: str

    def build_profile(self) -> MaterialProfileIdentity: ...

    def build_atom_groups(self, profile: MaterialProfileIdentity) -> AtomGroupCatalog: ...

    def build_condition_axes(self, profile: MaterialProfileIdentity) -> ConditionAxisCatalog: ...

    def build_independence_axes(self, profile: MaterialProfileIdentity) -> IndependenceAxisCatalog: ...


def build_single_phase_material_profile(
    *,
    profile_id: str,
    phase_kind: MaterialPhaseKind | str,
    geometry: MaterialGeometryKind | str = MaterialGeometryKind.BULK,
    chemistry_modifiers: tuple[str, ...] = (),
    extensions: tuple[str, ...] = (),
    profile_version: str = "1",
    phase_id: str = "material",
    atom_group_id: str = "all_atoms",
    provider_identity: MaterialProfileProviderIdentity | None = None,
    notes: tuple[str, ...] = (),
) -> MaterialProfileIdentity:
    """Build an explicit one-phase profile without activating any extension."""

    return MaterialProfileIdentity(
        profile_id=profile_id,
        profile_version=profile_version,
        phases=(
            PhaseComponentIdentity(
                phase_id=phase_id,
                phase_kind=MaterialPhaseKind(phase_kind),
                atom_group_ids=(atom_group_id,),
                chemistry_modifiers=chemistry_modifiers,
            ),
        ),
        geometry=MaterialGeometryKind(geometry),
        chemistry_modifiers=chemistry_modifiers,
        extensions=extensions,
        provider_identity=provider_identity,
        user_declared=True,
        notes=notes,
    )


def default_atom_group_catalog(profile: MaterialProfileIdentity) -> AtomGroupCatalog:
    """Return the safe one-phase all-atoms catalog.

    Multi-phase and interface systems require explicit group membership because
    silently assigning all atoms to every phase would destroy phase identity.
    """

    if len(profile.phases) != 1 or profile.atom_group_ids != ("all_atoms",):
        raise TrainingDataInputError(
            "Automatic atom-group construction is available only for one-phase profiles using the 'all_atoms' group."
        )
    phase = profile.phases[0]
    return AtomGroupCatalog(
        material_profile_digest=profile.content_digest,
        material_phase_ids=profile.phase_ids,
        groups=(
            AtomGroupDefinition(
                group_id="all_atoms",
                label="All atoms",
                selector=AtomGroupSelector(kind=AtomGroupSelectorKind.ALL_ATOMS),
                phase_ids=(phase.phase_id,),
                roles=("all_atoms",),
            ),
        ),
        notes=("Generic one-phase fallback; no material-specific groups are inferred.",),
    )


def default_condition_axis_catalog(profile: MaterialProfileIdentity) -> ConditionAxisCatalog:
    """Return baseline condition identities without assigning observed values."""

    return ConditionAxisCatalog(
        material_profile_digest=profile.content_digest,
        axes=(
            ConditionAxisDefinition(
                axis_id="composition",
                label="Chemical composition",
                value_kind=AxisValueKind.CATEGORICAL,
                roles=(ConditionAxisRole.COVERAGE, ConditionAxisRole.STRATIFICATION),
                required=True,
            ),
            ConditionAxisDefinition(
                axis_id="temperature_kelvin",
                label="Temperature",
                value_kind=AxisValueKind.CONTINUOUS,
                roles=(ConditionAxisRole.COVERAGE, ConditionAxisRole.CHALLENGE),
                unit="K",
                minimum=0.0,
            ),
            ConditionAxisDefinition(
                axis_id="pressure",
                label="Pressure",
                value_kind=AxisValueKind.CONTINUOUS,
                roles=(ConditionAxisRole.COVERAGE, ConditionAxisRole.CHALLENGE),
                unit="eV/angstrom^3",
            ),
            ConditionAxisDefinition(
                axis_id="regime",
                label="Preparation or trajectory regime",
                value_kind=AxisValueKind.CATEGORICAL,
                roles=(ConditionAxisRole.STRATIFICATION, ConditionAxisRole.REPORTING),
            ),
        ),
    )


def default_independence_axis_catalog(profile: MaterialProfileIdentity) -> IndependenceAxisCatalog:
    """Return conservative generic independence axes.

    These definitions do not assert that independent values exist.  DATA5 must
    still supply evidence before assigning an independence grade.
    """

    return IndependenceAxisCatalog(
        material_profile_digest=profile.content_digest,
        axes=(
            IndependenceAxisDefinition(
                axis_id="trajectory_run",
                label="Independent trajectory or static source run",
                scope=IndependenceAxisScope.TRAJECTORY,
                required_for_roles=("outer_monitor", "locked_interpolation_test"),
                minimum_distinct_values=2,
                leakage_barrier=True,
            ),
            IndependenceAxisDefinition(
                axis_id="initial_configuration",
                label="Independent initial structural realization",
                scope=IndependenceAxisScope.INITIAL_CONFIGURATION,
                required_for_roles=("locked_interpolation_test",),
                minimum_distinct_values=2,
                leakage_barrier=True,
            ),
        ),
    )


def build_material_profile_contracts(
    profile: MaterialProfileIdentity,
    *,
    atom_groups: AtomGroupCatalog | None = None,
    condition_axes: ConditionAxisCatalog | None = None,
    independence_axes: IndependenceAxisCatalog | None = None,
    notes: tuple[str, ...] = (),
) -> MaterialProfileContracts:
    """Build the immutable aggregate used by later MLFF stages."""

    return MaterialProfileContracts(
        profile=profile,
        atom_groups=default_atom_group_catalog(profile) if atom_groups is None else atom_groups,
        condition_axes=default_condition_axis_catalog(profile) if condition_axes is None else condition_axes,
        independence_axes=default_independence_axis_catalog(profile) if independence_axes is None else independence_axes,
        notes=notes,
    )


def contracts_from_provider(provider: SystemProfileProvider) -> MaterialProfileContracts:
    """Materialize and cross-check one provider's declarative contracts."""

    profile = provider.build_profile()
    if profile.provider_identity is None:
        raise TrainingDataInputError("Provider-materialized profiles require a provider_identity.")
    if profile.provider_identity.provider_id != _identifier(provider.provider_id, name="provider_id"):
        raise TrainingDataInputError("Provider identity does not match the material profile.")
    if profile.provider_identity.provider_version != _nonempty_text(provider.provider_version, name="provider_version"):
        raise TrainingDataInputError("Provider version does not match the material profile.")
    return MaterialProfileContracts(
        profile=profile,
        atom_groups=provider.build_atom_groups(profile),
        condition_axes=provider.build_condition_axes(profile),
        independence_axes=provider.build_independence_axes(profile),
    )


def resolve_atom_group_indices(
    catalog: AtomGroupCatalog,
    atomic_numbers: tuple[int, ...] | list[int] | Any,
    group_id: str,
) -> tuple[int, ...]:
    """Resolve a static atom-group selector against one atomic-number sequence.

    Metadata- and provider-defined dynamic groups intentionally require their
    registered membership provider and fail closed here.
    """

    numbers = tuple(int(v) for v in atomic_numbers)
    groups = {group.group_id: group for group in catalog.groups}
    cache: dict[str, set[int]] = {}

    def resolve(current: str) -> set[int]:
        if current in cache:
            return set(cache[current])
        if current not in groups:
            raise TrainingDataInputError(f"Unknown atom group {current!r}.")
        definition = groups[current]
        selector = definition.selector
        if selector.kind is AtomGroupSelectorKind.ALL_ATOMS:
            result = set(range(len(numbers)))
        elif selector.kind is AtomGroupSelectorKind.ATOMIC_NUMBERS:
            allowed = set(selector.atomic_numbers)
            result = {index for index, number in enumerate(numbers) if number in allowed}
        elif selector.kind is AtomGroupSelectorKind.ATOM_INDICES:
            result = set(selector.atom_indices)
            if any(index >= len(numbers) for index in result):
                raise TrainingDataInputError(f"Atom group {current!r} contains an out-of-range atom index.")
        elif selector.kind is AtomGroupSelectorKind.COMPOSITE:
            operands = [resolve(group) for group in selector.source_group_ids]
            if selector.operation is AtomGroupSetOperation.UNION:
                result = set().union(*operands)
            elif selector.operation is AtomGroupSetOperation.INTERSECTION:
                result = set(operands[0]).intersection(*operands[1:])
            elif selector.operation is AtomGroupSetOperation.DIFFERENCE:
                result = set(operands[0]).difference(*operands[1:])
            elif selector.operation is AtomGroupSetOperation.COMPLEMENT:
                result = set(range(len(numbers))).difference(operands[0])
            else:
                raise TrainingDataInputError("Unsupported composite atom-group operation.")
        else:
            raise TrainingDataInputError(
                f"Atom group {current!r} is frame-dynamic and requires a membership provider."
            )
        if not result and not definition.allow_empty:
            raise TrainingDataInputError(f"Atom group {current!r} resolved to an empty set.")
        cache[current] = set(result)
        return result

    return tuple(sorted(resolve(str(group_id))))


def focus_atom_group_ids(contracts: MaterialProfileContracts | None) -> tuple[str, ...]:
    """Return explicitly declared MLFF focus groups, never chemistry guesses."""

    if contracts is None:
        return ()
    focus_roles = {"mlff_focus", "training_focus", "validation_focus"}
    return tuple(
        group.group_id
        for group in contracts.atom_groups.groups
        if focus_roles.intersection(group.roles)
    )


def focus_atomic_numbers(
    contracts: MaterialProfileContracts | None,
    atomic_numbers: tuple[int, ...] | list[int] | Any,
) -> tuple[int, ...]:
    """Resolve explicit focus groups to species; fall back to all present species."""

    numbers = tuple(int(v) for v in atomic_numbers)
    group_ids = focus_atom_group_ids(contracts)
    if not group_ids:
        return tuple(sorted(set(numbers)))
    indices: set[int] = set()
    for group_id in group_ids:
        try:
            indices.update(resolve_atom_group_indices(contracts.atom_groups, numbers, group_id))
        except TrainingDataInputError:
            # Dynamic groups cannot be reduced to species safely.  Use all
            # species rather than silently dropping difficult environments.
            return tuple(sorted(set(numbers)))
    return tuple(sorted({numbers[index] for index in indices}))
