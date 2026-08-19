"""GFX3D-4 scientific dependency-provider contracts.

The universal layer graph consumes product-level dependencies.  A source
provider may batch preparation internally when the owning scientific subsystem
has a qualified joint planner, but layers never depend on that composite batch
object as their scientific dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

import numpy as np

from .contracts import GraphicsDependencyKey
from .context import GraphicsSceneContext
from .errors import Graphics3DDependencyError

FRAMEWORK_PRODUCT_PROVIDER = "framework_topology_product"
CONNECTIVITY_PRODUCT_PROVIDER = "atomic_connectivity_product"
TRAJECTORY_PRODUCT_PROVIDER = "atomic_trajectory_product"
DENSITY_PRODUCT_PROVIDER = "atomic_density_product"
PRODUCT_PROVIDER_TYPES = frozenset(
    {
        FRAMEWORK_PRODUCT_PROVIDER,
        CONNECTIVITY_PRODUCT_PROVIDER,
        TRAJECTORY_PRODUCT_PROVIDER,
        DENSITY_PRODUCT_PROVIDER,
    }
)


@dataclass(frozen=True, slots=True)
class GraphicsScientificProduct:
    """One prepared scientific product exposed to a GFX3D layer.

    The product carries only renderer-neutral scientific payload plus minimal
    scene-coordinate metadata.  In particular, it must never embed the owning
    composite ``FrameworkDynamicsScene``: that would reintroduce the monolithic
    dependency authority removed by GFX3D-4/5.
    """

    provider_type: str
    value: Any
    display_cell: Any = None
    frame_indices: tuple[int, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider = str(self.provider_type).strip().lower()
        if provider not in PRODUCT_PROVIDER_TYPES:
            raise Graphics3DDependencyError(f"Unknown GFX3D scientific product provider {provider!r}.")
        object.__setattr__(self, "provider_type", provider)
        if self.display_cell is not None:
            cell = np.array(self.display_cell, dtype=np.float64, copy=True, order="C")
            if cell.shape != (3, 3) or np.any(~np.isfinite(cell)) or abs(float(np.linalg.det(cell))) <= 1.0e-12:
                raise Graphics3DDependencyError("GraphicsScientificProduct display_cell must be a finite nonsingular 3x3 matrix.")
            cell.setflags(write=False)
            object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "frame_indices", tuple(int(v) for v in self.frame_indices))
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))


@dataclass(frozen=True, slots=True)
class GraphicsDensityProduct:
    """Renderer-neutral bundle of prepared density fields and atom identities."""

    atomic_density_fields: tuple[Any, ...] = ()
    framework_density_fields: Any = None
    atomic_number_by_atom: Mapping[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "atomic_density_fields", tuple(self.atomic_density_fields))
        object.__setattr__(
            self,
            "atomic_number_by_atom",
            MappingProxyType({int(k): int(v) for k, v in dict(self.atomic_number_by_atom).items()}),
        )



@runtime_checkable
class Graphics3DDependencySource(Protocol):
    """Source-side product resolver used by the GFX3D-4 dependency DAG."""

    def dependency_key(self, provider_type: str) -> GraphicsDependencyKey: ...

    def resolve_graphics3d_dependency(
        self, key: GraphicsDependencyKey, context: GraphicsSceneContext
    ) -> GraphicsScientificProduct: ...


def source_dependency_key(context: GraphicsSceneContext, provider_type: str) -> GraphicsDependencyKey:
    source = context.source
    if isinstance(source, Graphics3DDependencySource):
        return source.dependency_key(provider_type)
    raise Graphics3DDependencyError(
        f"The current GFX3D source does not provide product dependency {provider_type!r}."
    )


def resolve_source_dependency(
    key: GraphicsDependencyKey, context: GraphicsSceneContext
) -> GraphicsScientificProduct:
    source = context.source
    if not isinstance(source, Graphics3DDependencySource):
        raise Graphics3DDependencyError(
            "GFX3D product-level dependency resolution requires a Graphics3DDependencySource."
        )
    result = source.resolve_graphics3d_dependency(key, context)
    if not isinstance(result, GraphicsScientificProduct):
        raise Graphics3DDependencyError(
            f"Source resolver for {key.provider_type!r} did not return GraphicsScientificProduct."
        )
    if result.provider_type != key.provider_type:
        raise Graphics3DDependencyError(
            f"Source returned product {result.provider_type!r} for requested {key.provider_type!r}."
        )
    return result
