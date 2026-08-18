"""Standardized, analysis-owned dispatch for physical observable calculations.

This module does not implement RDFs, coordination, spectra, diffusion, or any
other scientific observable. It provides a stable, versioned call/recipe surface
that delegates to authoritative analysis modules. MLFF workflows may invoke this
surface without importing implementation details or taking ownership of the
underlying scientific algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import platform
import sys
import time
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence
import warnings

import numpy as np
import scipy
from ase.data import atomic_numbers

from mdstats._version import __version__ as MDSTATS_EXECUTING_VERSION

from .atomic_connectivity import (
    ConnectivityScope,
    DistanceConnectivity,
    HystereticDistanceConnectivity,
    ReferenceDistanceConnectivity,
    compute_atomic_connectivity,
)
from .bond_angle import CoordinationCondition, compute_bond_angle_distribution
from .coordination import compute_coordination_distribution
from .current_correlation import compute_charge_current, compute_current_correlation
from .cutoffs import PairCutoff, PairCutoffRegistry
from .diffusion import compare_msd_vacf_diffusion, estimate_diffusion_plateau
from .displacement_dynamics import (
    compute_non_gaussian_parameter,
    compute_self_intermediate_scattering,
    compute_self_van_hove,
)
from .ionic_conductivity import (
    compute_nernst_einstein_comparison,
    estimate_ionic_conductivity_plateau,
    integrate_ionic_conductivity,
)
from .msd import compute_msd
from .rdf import compute_pair_rdf
from .topology_statistics import compute_atomic_connectivity_statistics
from .vacf import compute_vacf
from .vacf_transport import integrate_vacf_to_diffusion, reconstruct_msd_from_vacf
from .velocity_spectrum import compute_vacf_spectrum, compute_vdos, compute_velocity_spectrum

OBSERVABLE_ANALYSIS_CALL_SCHEMA = "mdstats.observable-analysis-call.v2"
OBSERVABLE_ANALYSIS_RECIPE_SCHEMA = "mdstats.observable-analysis-recipe.v2"
OBSERVABLE_ANALYSIS_API_VERSION = "mdstats.observable-validation.2026-07.v2"
OBSERVABLE_CAPABILITY_SCHEMA = "mdstats.observable-capability.v3"
OBSERVABLE_RESULT_IDENTITY_SCHEMA = "mdstats.observable-result-identity.v1"


class ObservableAnalysisError(ValueError):
    """Base class for standardized observable-call failures."""


class UnknownObservableError(ObservableAnalysisError):
    """Raised when a call names an observable that is not registered."""


class ObservableDependencyError(ObservableAnalysisError):
    """Raised when a recipe dependency is absent, cyclic, forward, or invalid."""


class ObservableParameterError(ObservableAnalysisError):
    """Raised when standardized parameters cannot be decoded safely."""


class ObservableRequirementError(ObservableAnalysisError):
    """Raised when a collection does not satisfy a capability precondition."""


class ObservableResultIdentityError(ObservableAnalysisError):
    """Raised when an analysis result cannot be identified canonically."""


class ObservableDomain(str, Enum):
    STRUCTURE = "structure"
    TOPOLOGY = "topology"
    DYNAMICS = "dynamics"
    SPECTRUM = "spectrum"
    TRANSPORT = "transport"


class CollectionRequirement(str, Enum):
    """Machine-checkable requirements on an ``AtomisticFrameCollection``."""

    POSITIONS_AND_CELLS = "positions_and_cells"
    ATOMIC_NUMBERS = "atomic_numbers"
    FIXED_POPULATION = "fixed_population"
    PERIODIC_GEOMETRY = "periodic_geometry"
    TRAJECTORY_SEMANTICS = "trajectory_semantics"
    TIME_AXIS = "time_axis"
    VELOCITIES = "velocities"
    STRESSES = "stresses"
    ENERGIES = "energies"


def _json_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.value
    return value


def _freeze_json(value: Any, *, path: str = "value") -> Any:
    value = _json_scalar(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not np.isfinite(value):
            raise ObservableParameterError(f"{path} must not contain nonfinite floats.")
        return value
    if isinstance(value, np.ndarray):
        return tuple(_freeze_json(v, path=f"{path}[]") for v in value.tolist())
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(v, path=f"{path}[]") for v in value)
    if isinstance(value, Mapping):
        items: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ObservableParameterError(f"{path} mapping keys must be non-empty strings.")
            items[key] = _freeze_json(item, path=f"{path}.{key}")
        return MappingProxyType(dict(sorted(items.items())))
    raise ObservableParameterError(
        f"{path} must be JSON-compatible; received {type(value).__name__}."
    )


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _thaw_json(_freeze_json(value)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _binding_references(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        refs: list[str] = []
        for item in value.values():
            refs.extend(_binding_references(item))
        return tuple(refs)
    if isinstance(value, (list, tuple)):
        refs = []
        for item in value:
            refs.extend(_binding_references(item))
        return tuple(refs)
    raise ObservableDependencyError(
        "Input bindings must contain call IDs or nested mappings/lists of call IDs."
    )


@dataclass(frozen=True, slots=True)
class ObservableCapability:
    """Versioned registry metadata for one analysis-owned observable."""

    observable_id: str
    domain: ObservableDomain
    owner_module: str
    owner_manual: str
    owner_manual_source_path: str
    owner_manual_uri: str
    function_name: str
    collection_requirements: tuple[CollectionRequirement, ...] = ()
    dependency_arguments: tuple[str, ...] = ()
    binding_only_arguments: tuple[str, ...] = ()
    required_arguments: tuple[str, ...] = ()
    one_of_argument_groups: tuple[tuple[str, ...], ...] = ()
    supported_arguments: tuple[str, ...] = ()
    parameter_schema_version: str = "v1"
    owner_api_version: str = ""
    parameter_codec_id: str = "json-direct.v1"
    result_type_hint: str = ""
    implementation_status: str = "implemented-and-regression-tested"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.observable_id.strip() or not self.owner_module.strip() or not self.function_name.strip():
            raise ObservableParameterError("Observable capability identifiers must be non-empty.")
        requirements = tuple(CollectionRequirement(v) for v in self.collection_requirements)
        object.__setattr__(self, "collection_requirements", requirements)
        object.__setattr__(self, "dependency_arguments", tuple(self.dependency_arguments))
        object.__setattr__(self, "binding_only_arguments", tuple(self.binding_only_arguments))
        object.__setattr__(self, "required_arguments", tuple(self.required_arguments))
        object.__setattr__(self, "one_of_argument_groups", tuple(tuple(v) for v in self.one_of_argument_groups))
        object.__setattr__(self, "supported_arguments", tuple(self.supported_arguments))
        if not self.parameter_schema_version or not self.owner_api_version or not self.parameter_codec_id:
            raise ObservableParameterError("Capability schema and API identifiers must be non-empty.")

    @property
    def required_collection_fields(self) -> tuple[str, ...]:
        """Deprecated compatibility alias for pre-v2 callers."""
        return tuple(item.value for item in self.collection_requirements)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_CAPABILITY_SCHEMA,
            "observable_id": self.observable_id,
            "domain": self.domain.value,
            "owner_module": self.owner_module,
            "owner_manual": self.owner_manual,
            "owner_manual_source_path": self.owner_manual_source_path,
            "owner_manual_uri": self.owner_manual_uri,
            "function_name": self.function_name,
            "collection_requirements": [v.value for v in self.collection_requirements],
            "dependency_arguments": list(self.dependency_arguments),
            "binding_only_arguments": list(self.binding_only_arguments),
            "required_arguments": list(self.required_arguments),
            "one_of_argument_groups": [list(v) for v in self.one_of_argument_groups],
            "supported_arguments": list(self.supported_arguments),
            "parameter_schema_version": self.parameter_schema_version,
            "owner_api_version": self.owner_api_version,
            "parameter_codec_id": self.parameter_codec_id,
            "result_type_hint": self.result_type_hint,
            "implementation_status": self.implementation_status,
            "notes": self.notes,
        }

    @property
    def content_digest(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}


@dataclass(frozen=True, slots=True)
class ObservableAnalysisCall:
    """Immutable JSON-safe call to one authoritative analysis function."""

    call_id: str
    observable_id: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    input_bindings: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    api_version: str = OBSERVABLE_ANALYSIS_API_VERSION

    def __post_init__(self) -> None:
        if not self.call_id.strip() or not self.observable_id.strip():
            raise ObservableParameterError("call_id and observable_id must be non-empty.")
        object.__setattr__(self, "parameters", _freeze_json(self.parameters, path="parameters"))
        object.__setattr__(self, "input_bindings", _freeze_json(self.input_bindings, path="input_bindings"))
        object.__setattr__(self, "tags", tuple(sorted({str(v) for v in self.tags if str(v)})))
        if not self.api_version.strip():
            raise ObservableParameterError("api_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_ANALYSIS_CALL_SCHEMA,
            "api_version": self.api_version,
            "call_id": self.call_id,
            "observable_id": self.observable_id,
            "parameters": _thaw_json(self.parameters),
            "input_bindings": _thaw_json(self.input_bindings),
            "tags": list(self.tags),
        }

    @property
    def content_digest(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableAnalysisCall":
        schema = payload.get("schema")
        if schema not in (OBSERVABLE_ANALYSIS_CALL_SCHEMA, "mdstats.observable-analysis-call.v1"):
            raise ObservableParameterError("Unsupported observable-analysis-call schema.")
        result = cls(
            call_id=str(payload["call_id"]),
            observable_id=str(payload["observable_id"]),
            parameters=payload.get("parameters", {}),
            input_bindings=payload.get("input_bindings", {}),
            tags=tuple(str(v) for v in payload.get("tags", ())),
            api_version=(
                OBSERVABLE_ANALYSIS_API_VERSION
                if schema == "mdstats.observable-analysis-call.v1"
                else str(payload.get("api_version", OBSERVABLE_ANALYSIS_API_VERSION))
            ),
        )
        # Legacy digests were calculated under the v1 schema and cannot equal v2.
        if schema == OBSERVABLE_ANALYSIS_CALL_SCHEMA and payload.get("content_digest") not in (None, result.content_digest):
            raise ObservableParameterError("Observable-analysis-call digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableAnalysisRecipe:
    """Ordered dependency-safe sequence of observable calls.

    Dependency safety is validated at construction: every binding must reference
    a preceding call, self/forward references are rejected, required dependency
    arguments must be bound, and all calls must use the recipe API version.
    """

    recipe_id: str
    calls: tuple[ObservableAnalysisCall, ...]
    purpose: str = "physical-observable-validation"
    api_version: str = OBSERVABLE_ANALYSIS_API_VERSION

    def __post_init__(self) -> None:
        if not self.recipe_id.strip() or not self.purpose.strip():
            raise ObservableParameterError("recipe_id and purpose must be non-empty.")
        calls = tuple(self.calls)
        if not calls:
            raise ObservableParameterError("An observable recipe must contain at least one call.")
        ids = [call.call_id for call in calls]
        if len(set(ids)) != len(ids):
            raise ObservableDependencyError("Observable recipe call IDs must be unique.")
        if any(call.api_version != self.api_version for call in calls):
            raise ObservableDependencyError("All calls must use the recipe API version.")

        all_ids = set(ids)
        preceding: set[str] = set()
        for call in calls:
            capability = get_observable_capability(call.observable_id)
            supplied = set(call.parameters) | set(call.input_bindings)
            unknown = supplied - set(capability.supported_arguments)
            if unknown:
                raise ObservableParameterError(
                    f"Call {call.call_id!r} supplies unsupported arguments for "
                    f"{call.observable_id!r}: {sorted(unknown)}."
                )
            illegal_parameters = set(call.parameters).intersection(capability.binding_only_arguments)
            if illegal_parameters:
                raise ObservableParameterError(
                    f"Call {call.call_id!r} arguments {sorted(illegal_parameters)} must be "
                    "supplied by input_bindings from prior native results."
                )
            missing = set(capability.required_arguments) - supplied
            if missing:
                raise ObservableParameterError(
                    f"Call {call.call_id!r} is missing required arguments: {sorted(missing)}."
                )
            for group in capability.one_of_argument_groups:
                if not supplied.intersection(group):
                    raise ObservableParameterError(
                        f"Call {call.call_id!r} requires one of {list(group)}."
                    )
            missing_dependencies = set(capability.dependency_arguments) - set(call.input_bindings)
            if missing_dependencies:
                raise ObservableDependencyError(
                    f"Call {call.call_id!r} must bind dependency arguments "
                    f"{sorted(missing_dependencies)}."
                )
            refs = set(_binding_references(call.input_bindings))
            if call.call_id in refs:
                raise ObservableDependencyError(
                    f"Call {call.call_id!r} cannot depend on itself."
                )
            unknown_refs = refs - all_ids
            if unknown_refs:
                raise ObservableDependencyError(
                    f"Call {call.call_id!r} references unknown calls {sorted(unknown_refs)}."
                )
            forward = refs - preceding
            if forward:
                raise ObservableDependencyError(
                    f"Call {call.call_id!r} has forward dependencies {sorted(forward)}; "
                    "dependencies must appear earlier in the recipe."
                )
            preceding.add(call.call_id)
        object.__setattr__(self, "calls", calls)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_ANALYSIS_RECIPE_SCHEMA,
            "api_version": self.api_version,
            "recipe_id": self.recipe_id,
            "purpose": self.purpose,
            "calls": [call.to_dict() for call in self.calls],
        }

    @property
    def content_digest(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableAnalysisRecipe":
        schema = payload.get("schema")
        if schema not in (OBSERVABLE_ANALYSIS_RECIPE_SCHEMA, "mdstats.observable-analysis-recipe.v1"):
            raise ObservableParameterError("Unsupported observable-analysis-recipe schema.")
        result = cls(
            recipe_id=str(payload["recipe_id"]),
            purpose=str(payload.get("purpose", "physical-observable-validation")),
            api_version=OBSERVABLE_ANALYSIS_API_VERSION,
            calls=tuple(ObservableAnalysisCall.from_dict(item) for item in payload["calls"]),
        )
        if schema == OBSERVABLE_ANALYSIS_RECIPE_SCHEMA and payload.get("content_digest") not in (None, result.content_digest):
            raise ObservableParameterError("Observable-analysis-recipe digest mismatch.")
        return result




def _stable_result_node(value: Any, *, path: str = "result") -> Any:
    """Convert a native analysis result into a compact canonical identity tree."""

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            return {"kind": "float", "value": repr(value)}
        return value
    if isinstance(value, np.generic):
        return _stable_result_node(value.item(), path=path)
    if isinstance(value, Enum):
        return {
            "kind": "enum",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "value": _stable_result_node(value.value, path=path),
        }
    if isinstance(value, np.ndarray):
        array = np.asarray(value)
        if array.dtype.kind == "O":
            raise ObservableResultIdentityError(
                f"{path} contains an object-dtype array, which has no stable byte identity."
            )
        if array.dtype.kind in {"U", "S"}:
            payload = _canonical_json(array.tolist()).encode("utf-8")
        else:
            payload = np.ascontiguousarray(array).view(np.uint8).tobytes()
        return {
            "kind": "ndarray",
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "kind": "dataclass",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": {
                item.name: _stable_result_node(getattr(value, item.name), path=f"{path}.{item.name}")
                for item in fields(value)
            },
        }
    if isinstance(value, Mapping):
        return {
            "kind": "mapping",
            "items": {
                str(key): _stable_result_node(item, path=f"{path}.{key}")
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            },
        }
    if isinstance(value, (list, tuple)):
        return {
            "kind": "sequence",
            "type": type(value).__name__,
            "items": [
                _stable_result_node(item, path=f"{path}[{index}]")
                for index, item in enumerate(value)
            ],
        }
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return {
            "kind": "to_dict",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "value": _stable_result_node(to_dict(), path=f"{path}.to_dict"),
        }
    raise ObservableResultIdentityError(
        f"{path} of type {type(value).__module__}.{type(value).__qualname__} "
        "does not provide a stable analysis-owned identity representation."
    )


@dataclass(frozen=True, slots=True)
class ObservableResultIdentity:
    """Analysis-owned immutable identity of one native scientific result."""

    call_id: str
    observable_id: str
    result_type: str
    serializer_id: str
    content_digest: str

    def __post_init__(self) -> None:
        if not self.call_id.strip() or not self.observable_id.strip() or not self.result_type.strip():
            raise ObservableResultIdentityError("Observable result identity fields must be non-empty.")
        if not self.serializer_id.strip():
            raise ObservableResultIdentityError("serializer_id must be non-empty.")
        if len(self.content_digest) != 64 or any(ch not in "0123456789abcdef" for ch in self.content_digest):
            raise ObservableResultIdentityError("content_digest must be a lowercase SHA-256 digest.")

    @classmethod
    def from_result(
        cls,
        *,
        call_id: str,
        observable_id: str,
        result: Any,
    ) -> "ObservableResultIdentity":
        result_type = f"{type(result).__module__}.{type(result).__qualname__}"
        node = _stable_result_node(result)
        payload = {
            "schema": OBSERVABLE_RESULT_IDENTITY_SCHEMA,
            "call_id": call_id,
            "observable_id": observable_id,
            "result_type": result_type,
            "serializer_id": "mdstats.analysis-result-tree.v1",
            "result": node,
        }
        return cls(
            call_id=call_id,
            observable_id=observable_id,
            result_type=result_type,
            serializer_id="mdstats.analysis-result-tree.v1",
            content_digest=_digest(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_RESULT_IDENTITY_SCHEMA,
            "call_id": self.call_id,
            "observable_id": self.observable_id,
            "result_type": self.result_type,
            "serializer_id": self.serializer_id,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableResultIdentity":
        if payload.get("schema") != OBSERVABLE_RESULT_IDENTITY_SCHEMA:
            raise ObservableResultIdentityError("Unsupported observable-result identity schema.")
        return cls(
            call_id=str(payload["call_id"]),
            observable_id=str(payload["observable_id"]),
            result_type=str(payload["result_type"]),
            serializer_id=str(payload["serializer_id"]),
            content_digest=str(payload["content_digest"]),
        )


@dataclass(frozen=True, slots=True)
class ObservableExecutionResult:
    """Runtime results from one recipe; scientific result objects remain native."""

    recipe: ObservableAnalysisRecipe
    results: Mapping[str, Any]
    result_types: Mapping[str, str]
    result_identities: Mapping[str, ObservableResultIdentity]
    warnings_by_call: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    runtime_identity: Mapping[str, Any] = field(default_factory=dict)
    capability_digests: Mapping[str, str] = field(default_factory=dict)
    duration_seconds_by_call: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        results = dict(self.results)
        expected = {call.call_id for call in self.recipe.calls}
        if set(results) != expected:
            raise ObservableDependencyError("Execution results do not match the recipe call IDs.")
        types = {str(key): str(value) for key, value in self.result_types.items()}
        if set(types) != expected:
            raise ObservableDependencyError("Execution result types do not match the recipe call IDs.")
        identities = {str(key): value for key, value in self.result_identities.items()}
        if set(identities) != expected:
            raise ObservableDependencyError("Execution result identities do not match the recipe call IDs.")
        for call in self.recipe.calls:
            identity = identities[call.call_id]
            if identity.call_id != call.call_id or identity.observable_id != call.observable_id:
                raise ObservableDependencyError("Execution result identity does not match its recipe call.")
            if identity.result_type != types[call.call_id]:
                raise ObservableDependencyError("Execution result identity type does not match runtime type.")
        warning_map = {str(k): tuple(str(v) for v in vals) for k, vals in self.warnings_by_call.items()}
        if set(warning_map) != expected:
            raise ObservableDependencyError("Execution warning records do not match the recipe call IDs.")
        cap_map = {str(k): str(v) for k, v in self.capability_digests.items()}
        if set(cap_map) != expected:
            raise ObservableDependencyError("Capability digest records do not match the recipe call IDs.")
        duration_map = {str(k): float(v) for k, v in self.duration_seconds_by_call.items()}
        if set(duration_map) != expected:
            raise ObservableDependencyError("Duration records do not match the recipe call IDs.")
        if any((not np.isfinite(value) or value < 0.0) for value in duration_map.values()):
            raise ObservableParameterError("Execution durations must be finite and nonnegative.")
        object.__setattr__(self, "results", MappingProxyType(results))
        object.__setattr__(self, "result_types", MappingProxyType(types))
        object.__setattr__(self, "result_identities", MappingProxyType(identities))
        object.__setattr__(self, "warnings_by_call", MappingProxyType(warning_map))
        object.__setattr__(self, "runtime_identity", _freeze_json(self.runtime_identity, path="runtime_identity"))
        object.__setattr__(self, "capability_digests", MappingProxyType(cap_map))
        object.__setattr__(self, "duration_seconds_by_call", MappingProxyType(duration_map))


@dataclass(frozen=True, slots=True)
class _RegisteredObservable:
    capability: ObservableCapability
    function: Callable[..., Any]
    uses_collection: bool
    parameter_decoder: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _atomic_number(value: Any) -> int:
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, str):
        token = value.strip()
        if token.isdigit():
            number = int(token)
        else:
            try:
                number = int(atomic_numbers[token])
            except KeyError as exc:
                raise ObservableParameterError(f"Unknown chemical symbol {value!r}.") from exc
    else:
        raise ObservableParameterError(f"Invalid atomic-number token {value!r}.")
    if number <= 0:
        raise ObservableParameterError("Atomic numbers must be positive.")
    return number


def _decode_pair(value: Any) -> tuple[int, int]:
    if isinstance(value, str):
        for delimiter in ("-", ":", ",", "/"):
            if delimiter in value:
                parts = value.split(delimiter)
                if len(parts) == 2:
                    return tuple(sorted((_atomic_number(parts[0]), _atomic_number(parts[1]))))  # type: ignore[return-value]
        raise ObservableParameterError(f"Cannot parse species pair {value!r}.")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
        return tuple(sorted((_atomic_number(value[0]), _atomic_number(value[1]))))  # type: ignore[return-value]
    raise ObservableParameterError(f"Cannot parse species pair {value!r}.")


def _decode_cutoff_registry(value: Any) -> PairCutoffRegistry:
    if isinstance(value, PairCutoffRegistry):
        return value
    entries: list[tuple[tuple[int, int], float, str, Mapping[str, Any]]] = []
    if isinstance(value, Mapping):
        for pair, radius in value.items():
            entries.append((_decode_pair(pair), float(radius), "manual", {}))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            if not isinstance(item, Mapping):
                raise ObservableParameterError("Cutoff-list entries must be mappings.")
            pair = item.get("pair", item.get("species", item.get("atomic_numbers")))
            if pair is None or "radius" not in item:
                raise ObservableParameterError("Each cutoff entry requires pair/species and radius.")
            metadata = item.get("source_metadata", {})
            if not isinstance(metadata, Mapping):
                raise ObservableParameterError("source_metadata must be a mapping.")
            entries.append((
                _decode_pair(pair),
                float(item["radius"]),
                str(item.get("source", "manual")),
                dict(metadata),
            ))
    else:
        raise ObservableParameterError("Cutoff registry must be a mapping or list of entries.")
    return PairCutoffRegistry({
        pair: PairCutoff(pair, radius, source=source, source_metadata=metadata)
        for pair, radius, source, metadata in entries
    })


def _decode_scope(value: Any) -> ConnectivityScope:
    if value is None:
        return ConnectivityScope()
    if not isinstance(value, Mapping):
        raise ObservableParameterError("Connectivity scope must be a mapping.")

    def _numbers(name: str) -> tuple[int, ...] | None:
        raw = value.get(name)
        return None if raw is None else tuple(sorted({_atomic_number(v) for v in raw}))

    def _indices(name: str) -> tuple[int, ...] | None:
        raw = value.get(name)
        return None if raw is None else tuple(sorted({int(v) for v in raw}))

    return ConnectivityScope(
        included_species=_numbers("included_species"),
        included_atom_indices=_indices("included_atom_indices"),
        excluded_species=_numbers("excluded_species") or (),
        excluded_atom_indices=_indices("excluded_atom_indices") or (),
    )


def _decode_connectivity_definition(value: Any) -> Any:
    if isinstance(value, (DistanceConnectivity, HystereticDistanceConnectivity, ReferenceDistanceConnectivity)):
        return value
    if not isinstance(value, Mapping):
        raise ObservableParameterError("Connectivity definition must be a mapping.")
    kind = str(value.get("kind", "distance")).strip().lower()
    scope = _decode_scope(value.get("scope"))
    if kind == "distance":
        return DistanceConnectivity(_decode_cutoff_registry(value["cutoffs"]), scope=scope)
    if kind == "hysteretic":
        return HystereticDistanceConnectivity(
            formation_cutoffs=_decode_cutoff_registry(value["formation_cutoffs"]),
            breaking_cutoffs=_decode_cutoff_registry(value["breaking_cutoffs"]),
            scope=scope,
            initial_state=str(value.get("initial_state", "formation_cutoff")),
        )
    if kind == "reference":
        return ReferenceDistanceConnectivity(
            discovery_cutoffs=_decode_cutoff_registry(value["discovery_cutoffs"]),
            formation_cutoffs=_decode_cutoff_registry(value["formation_cutoffs"]),
            retention_cutoffs=_decode_cutoff_registry(value["retention_cutoffs"]),
            reference_frame=int(value.get("reference_frame", 0)),
            scope=scope,
        )
    raise ObservableParameterError(f"Unsupported standardized connectivity kind {kind!r}.")


def _decode_coordination_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    if "cutoff_registry" in parameters:
        parameters["cutoff_registry"] = _decode_cutoff_registry(parameters["cutoff_registry"])
    return parameters


def _decode_bond_angle_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    if "triplet" in parameters:
        parameters["triplet"] = tuple(parameters["triplet"])
    if "cutoffs" in parameters:
        parameters["cutoffs"] = _decode_cutoff_registry(parameters["cutoffs"])
    if "coordination_filters" in parameters:
        filters = []
        for item in parameters["coordination_filters"]:
            if isinstance(item, CoordinationCondition):
                filters.append(item)
            elif isinstance(item, Mapping):
                filters.append(CoordinationCondition(
                    neighbor_species=tuple(_atomic_number(v) for v in item["neighbor_species"]),
                    minimum=None if item.get("minimum") is None else int(item["minimum"]),
                    maximum=None if item.get("maximum") is None else int(item["maximum"]),
                ))
            else:
                raise ObservableParameterError("coordination_filters entries must be mappings.")
        parameters["coordination_filters"] = tuple(filters)
    if "angle_range" in parameters:
        parameters["angle_range"] = tuple(float(v) for v in parameters["angle_range"])
    return parameters


def _decode_connectivity_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    parameters["definition"] = _decode_connectivity_definition(parameters["definition"])
    return parameters




def _decode_tuple_parameters(*names: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a JSON decoder for owner APIs that require literal tuples."""

    def decode(parameters: dict[str, Any]) -> dict[str, Any]:
        for name in names:
            if name in parameters and parameters[name] is not None:
                value = parameters[name]
                if not isinstance(value, (list, tuple)):
                    raise ObservableParameterError(f"{name} must be a JSON array.")
                parameters[name] = tuple(value)
        return parameters

    return decode

def _function_metadata(function: Callable[..., Any], *, uses_collection: bool, unsupported: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...], str, str]:
    signature = inspect.signature(function)
    parameters = list(signature.parameters.values())
    if uses_collection and parameters:
        parameters = parameters[1:]
    supported = tuple(
        p.name for p in parameters
        if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        and p.name not in set(unsupported)
    )
    required = tuple(
        p.name for p in parameters
        if p.default is inspect.Parameter.empty
        and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        and p.name not in set(unsupported)
    )
    signature_text = f"{function.__module__}.{function.__qualname__}{signature}"
    try:
        implementation_text = inspect.getsource(function)
    except (OSError, TypeError):
        module = inspect.getmodule(function)
        module_path = None if module is None else getattr(module, "__file__", None)
        implementation_text = "" if module_path is None else Path(module_path).read_text(encoding="utf-8")
    owner_payload = signature_text + "\n" + implementation_text
    owner_api_version = f"python-source-sha256:{hashlib.sha256(owner_payload.encode()).hexdigest()}"
    result_hint = str(signature.return_annotation)
    return supported, required, owner_api_version, result_hint


def _cap(
    observable_id: str,
    domain: ObservableDomain,
    module: str,
    function: Callable[..., Any],
    *,
    manual_id: str,
    manual_source_path: str,
    requirements: Sequence[CollectionRequirement] = (),
    dependencies: Sequence[str] = (),
    binding_only: Sequence[str] = (),
    one_of: Sequence[Sequence[str]] = (),
    notes: str = "",
    uses_collection: bool,
    decoder: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    unsupported: Sequence[str] = (),
    codec: str = "json-direct.v1",
) -> _RegisteredObservable:
    supported, required, owner_api_version, result_hint = _function_metadata(
        function, uses_collection=uses_collection, unsupported=unsupported
    )
    return _RegisteredObservable(
        capability=ObservableCapability(
            observable_id=observable_id,
            domain=domain,
            owner_module=module,
            owner_manual=manual_id,
            owner_manual_source_path=manual_source_path,
            owner_manual_uri=f"mdstats-doc://{manual_id}/{MDSTATS_EXECUTING_VERSION}",
            function_name=function.__name__,
            collection_requirements=tuple(requirements),
            dependency_arguments=tuple(dependencies),
            binding_only_arguments=tuple(binding_only),
            required_arguments=required,
            one_of_argument_groups=tuple(tuple(v) for v in one_of),
            supported_arguments=supported,
            owner_api_version=owner_api_version,
            parameter_codec_id=codec,
            result_type_hint=result_hint,
            notes=(notes + (f" Unsupported owner options in standardized v1 codec: {', '.join(unsupported)}." if unsupported else "")).strip(),
        ),
        function=function,
        uses_collection=uses_collection,
        parameter_decoder=decoder,
    )


_STRUCTURAL_MANUAL_ID = "structural-observables-architecture"
_DYNAMICS_MANUAL_ID = "vacf-dynamics-architecture"
_TOPOLOGY_MANUAL_ID = "topology-statistics-architecture"
_STRUCTURAL_MANUAL_PATH = "docs/arch_manuals/structural_observables_architecture.md"
_DYNAMICS_MANUAL_PATH = "docs/arch_manuals/vacf_dynamics_architecture.md"
_TOPOLOGY_MANUAL_PATH = "docs/arch_manuals/topology_statistics_architecture.md"
_POS = (CollectionRequirement.POSITIONS_AND_CELLS, CollectionRequirement.ATOMIC_NUMBERS, CollectionRequirement.FIXED_POPULATION)
_TRAJ_POS = _POS + (CollectionRequirement.TRAJECTORY_SEMANTICS, CollectionRequirement.TIME_AXIS)
_TRAJ_VEL = (CollectionRequirement.ATOMIC_NUMBERS, CollectionRequirement.FIXED_POPULATION, CollectionRequirement.TRAJECTORY_SEMANTICS, CollectionRequirement.TIME_AXIS, CollectionRequirement.VELOCITIES)

_REGISTRY: dict[str, _RegisteredObservable] = {
    item.capability.observable_id: item
    for item in (
        _cap("structure.rdf", ObservableDomain.STRUCTURE, "mdstats.analysis.rdf", compute_pair_rdf, manual_id=_STRUCTURAL_MANUAL_ID, manual_source_path=_STRUCTURAL_MANUAL_PATH, requirements=_POS, uses_collection=True, unsupported=("neighbor_search_options",)),
        _cap("structure.coordination", ObservableDomain.STRUCTURE, "mdstats.analysis.coordination", compute_coordination_distribution, manual_id=_STRUCTURAL_MANUAL_ID, manual_source_path=_STRUCTURAL_MANUAL_PATH, requirements=_POS, dependencies=(), one_of=(("cutoff", "cutoff_registry", "rdf_result"),), binding_only=("rdf_result",), uses_collection=True, decoder=_decode_coordination_parameters, unsupported=("neighbor_search_options",), codec="coordination-json.v1"),
        _cap("structure.bond_angle", ObservableDomain.STRUCTURE, "mdstats.analysis.bond_angle", compute_bond_angle_distribution, manual_id=_STRUCTURAL_MANUAL_ID, manual_source_path=_STRUCTURAL_MANUAL_PATH, requirements=_POS, uses_collection=True, decoder=_decode_bond_angle_parameters, unsupported=("neighbor_search_options",), codec="bond-angle-json.v1"),
        _cap("topology.atomic_connectivity", ObservableDomain.TOPOLOGY, "mdstats.analysis.atomic_connectivity", compute_atomic_connectivity, manual_id=_STRUCTURAL_MANUAL_ID, manual_source_path=_STRUCTURAL_MANUAL_PATH, requirements=_POS, uses_collection=True, decoder=_decode_connectivity_parameters, unsupported=("neighbor_search_options", "verlet_cache_options"), codec="connectivity-json.v1"),
        _cap("topology.atomic_statistics", ObservableDomain.TOPOLOGY, "mdstats.analysis.topology_statistics", compute_atomic_connectivity_statistics, manual_id=_TOPOLOGY_MANUAL_ID, manual_source_path=_TOPOLOGY_MANUAL_PATH, dependencies=("catalog",), uses_collection=False, unsupported=("options",)),
        _cap("dynamics.msd", ObservableDomain.DYNAMICS, "mdstats.analysis.msd", compute_msd, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, requirements=_TRAJ_POS, uses_collection=True),
        _cap("dynamics.vacf", ObservableDomain.DYNAMICS, "mdstats.analysis.vacf", compute_vacf, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, requirements=_TRAJ_VEL, uses_collection=True),
        _cap("spectrum.vacf", ObservableDomain.SPECTRUM, "mdstats.analysis.velocity_spectrum", compute_vacf_spectrum, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("vacf",), uses_collection=False),
        _cap("spectrum.velocity_welch", ObservableDomain.SPECTRUM, "mdstats.analysis.velocity_spectrum", compute_velocity_spectrum, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, requirements=_TRAJ_VEL, uses_collection=True),
        _cap("spectrum.vdos", ObservableDomain.SPECTRUM, "mdstats.analysis.velocity_spectrum", compute_vdos, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("spectrum",), uses_collection=False),
        _cap("transport.vacf_diffusion", ObservableDomain.TRANSPORT, "mdstats.analysis.vacf_transport", integrate_vacf_to_diffusion, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("vacf",), uses_collection=False),
        _cap("transport.diffusion_plateau", ObservableDomain.TRANSPORT, "mdstats.analysis.diffusion", estimate_diffusion_plateau, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("running",), uses_collection=False, decoder=_decode_tuple_parameters("time_range_ps"), codec="time-range-json.v1"),
        _cap("dynamics.msd_from_vacf", ObservableDomain.DYNAMICS, "mdstats.analysis.vacf_transport", reconstruct_msd_from_vacf, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("vacf",), uses_collection=False),
        _cap("transport.msd_vacf_comparison", ObservableDomain.TRANSPORT, "mdstats.analysis.diffusion", compare_msd_vacf_diffusion, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("msd", "vacf_diffusion"), uses_collection=False, decoder=_decode_tuple_parameters("msd_fit_range_ps"), codec="time-range-json.v1"),
        _cap("dynamics.self_van_hove", ObservableDomain.DYNAMICS, "mdstats.analysis.displacement_dynamics", compute_self_van_hove, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, requirements=_TRAJ_POS, uses_collection=True),
        _cap("dynamics.non_gaussian", ObservableDomain.DYNAMICS, "mdstats.analysis.displacement_dynamics", compute_non_gaussian_parameter, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, requirements=_TRAJ_POS, uses_collection=True),
        _cap("dynamics.self_intermediate_scattering", ObservableDomain.DYNAMICS, "mdstats.analysis.displacement_dynamics", compute_self_intermediate_scattering, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, requirements=_TRAJ_POS, one_of=(("q_vectors", "q_magnitudes"),), uses_collection=True),
        _cap("transport.charge_current", ObservableDomain.TRANSPORT, "mdstats.analysis.current_correlation", compute_charge_current, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, requirements=_TRAJ_VEL, one_of=(("charges", "species_charges"),), uses_collection=True),
        _cap("transport.current_correlation", ObservableDomain.TRANSPORT, "mdstats.analysis.current_correlation", compute_current_correlation, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("current",), uses_collection=False),
        _cap("transport.ionic_conductivity", ObservableDomain.TRANSPORT, "mdstats.analysis.ionic_conductivity", integrate_ionic_conductivity, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("correlation",), uses_collection=False),
        _cap("transport.conductivity_plateau", ObservableDomain.TRANSPORT, "mdstats.analysis.ionic_conductivity", estimate_ionic_conductivity_plateau, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("running",), uses_collection=False, decoder=_decode_tuple_parameters("time_range_ps"), codec="time-range-json.v1"),
        _cap("transport.nernst_einstein_comparison", ObservableDomain.TRANSPORT, "mdstats.analysis.ionic_conductivity", compute_nernst_einstein_comparison, manual_id=_DYNAMICS_MANUAL_ID, manual_source_path=_DYNAMICS_MANUAL_PATH, dependencies=("conductivity", "species_diffusion"), uses_collection=False),
    )
}


def list_observable_capabilities(*, domain: ObservableDomain | str | None = None) -> tuple[ObservableCapability, ...]:
    resolved = None if domain is None else ObservableDomain(domain)
    capabilities = [entry.capability for entry in _REGISTRY.values()]
    if resolved is not None:
        capabilities = [item for item in capabilities if item.domain is resolved]
    return tuple(sorted(capabilities, key=lambda item: item.observable_id))


def get_observable_capability(observable_id: str) -> ObservableCapability:
    try:
        return _REGISTRY[observable_id].capability
    except KeyError as exc:
        raise UnknownObservableError(f"Unknown observable_id {observable_id!r}.") from exc


def _preflight_collection(collection: Any, capability: ObservableCapability) -> None:
    fractional = getattr(collection, "fractional_positions", None)
    cells = getattr(collection, "cells", None)
    numbers = getattr(collection, "atomic_numbers", None)
    times = getattr(collection, "times", None)
    velocities = getattr(collection, "velocities", None)

    for requirement in capability.collection_requirements:
        ok = True
        detail = ""
        if requirement is CollectionRequirement.POSITIONS_AND_CELLS:
            ok = (
                fractional is not None
                and cells is not None
                and np.ndim(fractional) == 3
                and np.shape(fractional)[-1] == 3
                and np.ndim(cells) == 3
                and np.shape(cells)[-2:] == (3, 3)
                and np.shape(cells)[0] == np.shape(fractional)[0]
                and np.all(np.isfinite(fractional))
                and np.all(np.isfinite(cells))
            )
            if ok:
                determinants = np.linalg.det(np.asarray(cells, dtype=np.float64))
                ok = bool(np.all(np.isfinite(determinants)) and np.all(np.abs(determinants) > 1.0e-12))
            detail = "finite (frames, atoms, 3) positions and nonsingular (frames, 3, 3) cells"
        elif requirement is CollectionRequirement.ATOMIC_NUMBERS:
            ok = (
                numbers is not None
                and np.ndim(numbers) == 1
                and np.size(numbers) > 0
                and np.all(np.asarray(numbers) > 0)
            )
            detail = "a positive one-dimensional atomic-number array"
        elif requirement is CollectionRequirement.FIXED_POPULATION:
            ok = (
                fractional is not None
                and numbers is not None
                and np.ndim(fractional) == 3
                and np.shape(fractional)[1] == np.shape(numbers)[0]
            )
            detail = "a fixed atom count matching atomic_numbers"
        elif requirement is CollectionRequirement.PERIODIC_GEOMETRY:
            pbc = getattr(collection, "pbc", None)
            ok = pbc is not None and cells is not None and bool(np.any(np.asarray(pbc, dtype=bool)))
            detail = "at least one periodic axis and valid cells"
        elif requirement is CollectionRequirement.TRAJECTORY_SEMANTICS:
            ok = bool(getattr(collection, "is_trajectory", False))
            detail = "trajectory semantics"
        elif requirement is CollectionRequirement.TIME_AXIS:
            ok = (
                bool(getattr(collection, "has_time_axis", False))
                and times is not None
                and np.ndim(times) == 1
                and np.size(times) == int(getattr(collection, "n_frames", -1))
                and np.all(np.isfinite(times))
                and (np.size(times) < 2 or np.all(np.diff(np.asarray(times, dtype=np.float64)) > 0.0))
            )
            detail = "a finite, strictly increasing time axis matching n_frames"
        elif requirement is CollectionRequirement.VELOCITIES:
            ok = (
                velocities is not None
                and fractional is not None
                and np.shape(velocities) == np.shape(fractional)
                and np.all(np.isfinite(velocities))
            )
            detail = "finite velocities matching the position array"
        elif requirement is CollectionRequirement.STRESSES:
            stresses = getattr(collection, "stresses", None)
            ok = stresses is not None and np.all(np.isfinite(stresses))
            detail = "finite stresses"
        elif requirement is CollectionRequirement.ENERGIES:
            energies = getattr(collection, "potential_energies", None)
            ok = energies is not None and np.all(np.isfinite(energies))
            detail = "finite potential energies"
        if not ok:
            raise ObservableRequirementError(
                f"Observable {capability.observable_id!r} requires {detail or requirement.value!r}."
            )


def _resolve_binding(value: Any, results: Mapping[str, Any], *, argument: str) -> Any:
    if isinstance(value, str):
        try:
            return results[value]
        except KeyError as exc:
            raise ObservableDependencyError(
                f"Binding for {argument!r} references unavailable call {value!r}."
            ) from exc
    if isinstance(value, Mapping):
        return {str(key): _resolve_binding(item, results, argument=f"{argument}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return tuple(_resolve_binding(item, results, argument=argument) for item in value)
    raise ObservableDependencyError(
        f"Binding for {argument!r} must be a call ID or nested mapping/list of call IDs."
    )


def execute_observable_call(
    collection: Any,
    call: ObservableAnalysisCall,
    *,
    resolved_results: Mapping[str, Any] | None = None,
) -> Any:
    try:
        registered = _REGISTRY[call.observable_id]
    except KeyError as exc:
        raise UnknownObservableError(f"Unknown observable_id {call.observable_id!r}.") from exc
    capability = registered.capability
    supplied = set(call.parameters) | set(call.input_bindings)
    unknown = supplied - set(capability.supported_arguments)
    if unknown:
        raise ObservableParameterError(
            f"Unsupported arguments for {call.observable_id!r}: {sorted(unknown)}."
        )
    parameters = _thaw_json(call.parameters)
    bindings = _thaw_json(call.input_bindings)
    prior = {} if resolved_results is None else resolved_results
    for argument, binding in bindings.items():
        if argument in parameters:
            raise ObservableParameterError(
                f"Argument {argument!r} is supplied by both parameters and input_bindings."
            )
        parameters[argument] = _resolve_binding(binding, prior, argument=argument)
    if registered.parameter_decoder is not None:
        parameters = registered.parameter_decoder(parameters)
    if registered.uses_collection:
        if collection is None:
            raise ObservableParameterError(
                f"Observable {call.observable_id!r} requires an AtomisticFrameCollection."
            )
        _preflight_collection(collection, capability)
        return registered.function(collection, **parameters)
    return registered.function(**parameters)


def _runtime_identity() -> dict[str, Any]:
    executing_file = Path(__file__).resolve()
    package_root = executing_file.parents[1]
    try:
        distribution_version = importlib.metadata.version("mdstats")
    except importlib.metadata.PackageNotFoundError:
        distribution_version = None
    try:
        ase_version = importlib.metadata.version("ase")
    except importlib.metadata.PackageNotFoundError:
        ase_version = "unknown"
    source_kind = "source-tree" if (package_root.parent / "pyproject.toml").exists() else "installed-package"
    return {
        "observable_api_version": OBSERVABLE_ANALYSIS_API_VERSION,
        "mdstats_executing_version": MDSTATS_EXECUTING_VERSION,
        "mdstats_distribution_version": distribution_version,
        "source_kind": source_kind,
        "executing_module": str(executing_file),
        "executing_module_sha256": hashlib.sha256(executing_file.read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "ase_version": ase_version,
    }


def execute_observable_recipe(collection: Any, recipe: ObservableAnalysisRecipe) -> ObservableExecutionResult:
    """Execute an ordered, construction-time validated recipe."""

    results: dict[str, Any] = {}
    result_types: dict[str, str] = {}
    result_identities: dict[str, ObservableResultIdentity] = {}
    warning_records: dict[str, tuple[str, ...]] = {}
    capability_digests: dict[str, str] = {}
    duration_seconds: dict[str, float] = {}
    for call in recipe.calls:
        capability = get_observable_capability(call.observable_id)
        started = time.perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = execute_observable_call(collection, call, resolved_results=results)
        duration_seconds[call.call_id] = max(0.0, time.perf_counter() - started)
        results[call.call_id] = result
        result_types[call.call_id] = f"{type(result).__module__}.{type(result).__qualname__}"
        result_identities[call.call_id] = ObservableResultIdentity.from_result(
            call_id=call.call_id,
            observable_id=call.observable_id,
            result=result,
        )
        warning_records[call.call_id] = tuple(
            f"{item.category.__name__}: {item.message}" for item in caught
        )
        capability_digests[call.call_id] = capability.content_digest
    return ObservableExecutionResult(
        recipe=recipe,
        results=results,
        result_types=result_types,
        result_identities=result_identities,
        warnings_by_call=warning_records,
        runtime_identity=_runtime_identity(),
        capability_digests=capability_digests,
        duration_seconds_by_call=duration_seconds,
    )
