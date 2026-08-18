"""Scientific-only density resource policy for Stage 11E0a.

This module excludes all rendering concepts.  Mesh cells, mesh faces, browser
trace counts, scene serialization, and HTML budgets are deliberately absent.
The current runtime resolver is called lazily because numerical resource
ownership is not moved until later extraction stages.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np

from .protocols import ScientificDensityInputError

SCIENTIFIC_DENSITY_RESOURCE_POLICY_SCHEMA = (
    "mdstats.scientific-density-resource-policy.v1"
)


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ScientificDensityInputError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise ScientificDensityInputError(f"{name} must be positive.")
    return result


def _positive_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise ScientificDensityInputError(f"{name} must be finite and positive.")
    return result


def _freeze_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _freeze_value(value.item())
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ScientificDensityInputError(
                "Resource metadata contains a non-finite float."
            )
        return float(value)
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): _freeze_value(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_value(item) for item in value)
    raise ScientificDensityInputError(
        f"Resource metadata contains unsupported value {type(value).__name__}."
    )


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _freeze_metadata(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = {} if value is None else dict(value)
    return MappingProxyType(
        {
            str(key): _freeze_value(item)
            for key, item in sorted(source.items(), key=lambda pair: str(pair[0]))
        }
    )


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


@dataclass(frozen=True, slots=True)
class ScientificDensityResourcePolicy:
    """Resolved limits used only to construct scientific density fields."""

    max_fields: int
    max_total_voxels: int
    max_samples: int
    max_nonzero_nodes: int
    max_stored_block_values: int
    max_blocks: int
    max_kernel_pairs: int
    max_planning_bytes: int
    max_workspace_bytes: int
    max_cic_contributions: int
    max_memory_bytes: int
    max_threads: int
    max_wall_time_seconds: float
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCIENTIFIC_DENSITY_RESOURCE_POLICY_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != SCIENTIFIC_DENSITY_RESOURCE_POLICY_SCHEMA:
            raise ScientificDensityInputError(
                f"Unsupported scientific resource schema {self.schema_version!r}."
            )
        for name in (
            "max_fields",
            "max_total_voxels",
            "max_samples",
            "max_nonzero_nodes",
            "max_stored_block_values",
            "max_blocks",
            "max_kernel_pairs",
            "max_planning_bytes",
            "max_workspace_bytes",
            "max_cic_contributions",
            "max_memory_bytes",
            "max_threads",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name))
        object.__setattr__(
            self,
            "max_wall_time_seconds",
            _positive_float(
                self.max_wall_time_seconds, name="max_wall_time_seconds"
            ),
        )
        if self.max_planning_bytes > self.max_memory_bytes:
            raise ScientificDensityInputError(
                "max_planning_bytes cannot exceed max_memory_bytes."
            )
        if self.max_workspace_bytes > self.max_memory_bytes:
            raise ScientificDensityInputError(
                "max_workspace_bytes cannot exceed max_memory_bytes."
            )
        metadata = _freeze_metadata(self.metadata)
        object.__setattr__(self, "metadata", metadata)
        payload = self.to_json_dict(include_signature=False)
        object.__setattr__(
            self,
            "signature",
            hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest(),
        )

    @classmethod
    def resolve(
        cls,
        *,
        max_memory_bytes: int | str | None = None,
        max_threads: int | None = None,
        max_wall_time_seconds: float | None = None,
        max_fields: int | None = None,
        max_total_voxels: int | None = None,
        max_samples: int | None = None,
        max_nonzero_nodes: int | None = None,
        max_stored_block_values: int | None = None,
        max_blocks: int | None = None,
        max_kernel_pairs: int | None = None,
        max_planning_bytes: int | None = None,
        max_workspace_bytes: int | None = None,
        max_cic_contributions: int | None = None,
    ) -> "ScientificDensityResourcePolicy":
        """Resolve runtime-derived scientific limits and optional tightenings.

        The lazy import is a compatibility bridge to the existing numerical
        resource owner.  The returned public policy contains no rendering
        fields and cannot carry a browser or mesh budget.
        """

        from ...plotting.runtime_resources import resolve_density_resource_limits

        budget, _time_model, derived = resolve_density_resource_limits(
            max_memory_bytes=max_memory_bytes,
            max_threads=max_threads,
            max_wall_time_seconds=max_wall_time_seconds,
        )

        def clamp(name: str, explicit: int | None) -> int:
            current = int(derived[name])
            if explicit is None:
                return current
            return min(current, _positive_int(explicit, name=name))

        planning = (
            budget.max_memory_bytes
            if max_planning_bytes is None
            else min(
                budget.max_memory_bytes,
                _positive_int(max_planning_bytes, name="max_planning_bytes"),
            )
        )
        workspace = (
            budget.max_memory_bytes
            if max_workspace_bytes is None
            else min(
                budget.max_memory_bytes,
                _positive_int(max_workspace_bytes, name="max_workspace_bytes"),
            )
        )
        contributions = (
            int(derived["max_density_kernel_pairs"])
            if max_cic_contributions is None
            else min(
                int(derived["max_density_kernel_pairs"]),
                _positive_int(
                    max_cic_contributions, name="max_cic_contributions"
                ),
            )
        )
        return cls(
            max_fields=clamp("max_density_fields", max_fields),
            max_total_voxels=clamp(
                "max_density_voxels", max_total_voxels
            ),
            max_samples=clamp("max_density_samples", max_samples),
            max_nonzero_nodes=clamp(
                "max_density_nonzero_nodes", max_nonzero_nodes
            ),
            max_stored_block_values=clamp(
                "max_density_stored_block_values", max_stored_block_values
            ),
            max_blocks=clamp("max_density_blocks", max_blocks),
            max_kernel_pairs=clamp(
                "max_density_kernel_pairs", max_kernel_pairs
            ),
            max_planning_bytes=planning,
            max_workspace_bytes=workspace,
            max_cic_contributions=contributions,
            max_memory_bytes=budget.max_memory_bytes,
            max_threads=budget.max_threads,
            max_wall_time_seconds=budget.max_wall_time_seconds,
            metadata={
                "resource_domain": "scientific_density",
                "resource_owner": "mdstats.analysis.density",
                "compatibility_resolver": "mdstats.plotting.runtime_resources",
                "rendering_fields_present": False,
            },
        )

    def to_legacy_keyword_arguments(self) -> dict[str, int]:
        """Translate into the current numerical producer's expert limits."""

        return {
            "max_fields": self.max_fields,
            "max_total_voxels": self.max_total_voxels,
            "max_samples": self.max_samples,
            "max_nonzero_nodes": self.max_nonzero_nodes,
            "max_stored_block_values": self.max_stored_block_values,
            "max_blocks": self.max_blocks,
            "max_kernel_pairs": self.max_kernel_pairs,
            "max_planning_bytes": self.max_planning_bytes,
            "max_workspace_bytes": self.max_workspace_bytes,
            "max_cic_contributions": self.max_cic_contributions,
        }

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "resource_domain": "scientific_density",
            "max_fields": self.max_fields,
            "max_total_voxels": self.max_total_voxels,
            "max_samples": self.max_samples,
            "max_nonzero_nodes": self.max_nonzero_nodes,
            "max_stored_block_values": self.max_stored_block_values,
            "max_blocks": self.max_blocks,
            "max_kernel_pairs": self.max_kernel_pairs,
            "max_planning_bytes": self.max_planning_bytes,
            "max_workspace_bytes": self.max_workspace_bytes,
            "max_cic_contributions": self.max_cic_contributions,
            "max_memory_bytes": self.max_memory_bytes,
            "max_threads": self.max_threads,
            "max_wall_time_seconds": self.max_wall_time_seconds,
            "metadata": _thaw_value(self.metadata),
        }
        if include_signature:
            result["signature"] = self.signature
        return result


def resolve_scientific_density_resources(
    policy: ScientificDensityResourcePolicy | None = None,
    **overrides: Any,
) -> ScientificDensityResourcePolicy:
    """Return an explicit scientific policy, resolving one when omitted."""

    if policy is not None:
        if overrides:
            raise ScientificDensityInputError(
                "Resource overrides cannot be combined with an explicit policy."
            )
        if not isinstance(policy, ScientificDensityResourcePolicy):
            raise TypeError(
                "policy must be ScientificDensityResourcePolicy or None."
            )
        return policy
    return ScientificDensityResourcePolicy.resolve(**overrides)


__all__ = [
    "SCIENTIFIC_DENSITY_RESOURCE_POLICY_SCHEMA",
    "ScientificDensityResourcePolicy",
    "resolve_scientific_density_resources",
]
