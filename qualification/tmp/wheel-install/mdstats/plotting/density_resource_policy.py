"""Rendering-only density resource policy.

Stage 11E0a separates browser/mesh admission from scientific field production.
This plotting-owned record may consume browser and mesh budgets; it is never an
argument to :mod:`mdstats.analysis.density` field construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .density_mesh_contracts import DensityMeshFaceContract
from .density_render_budget import BrowserMeshBudget
from .graph_errors import GraphStyleError

DENSITY_RENDERING_RESOURCE_POLICY_SCHEMA = (
    "mdstats.density-rendering-resource-policy.v1"
)


@dataclass(frozen=True, slots=True)
class DensityRenderingResourcePolicy:
    """Rendering budgets kept outside the scientific density facade."""

    browser_mesh_budget: BrowserMeshBudget
    mesh_face_contract: DensityMeshFaceContract
    cloud_max_points: int
    schema_version: str = DENSITY_RENDERING_RESOURCE_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_RENDERING_RESOURCE_POLICY_SCHEMA:
            raise GraphStyleError(
                f"Unsupported rendering resource schema {self.schema_version!r}."
            )
        if not isinstance(self.browser_mesh_budget, BrowserMeshBudget):
            raise TypeError("browser_mesh_budget must be BrowserMeshBudget.")
        if not isinstance(self.mesh_face_contract, DensityMeshFaceContract):
            raise TypeError("mesh_face_contract must be DensityMeshFaceContract.")
        if isinstance(self.cloud_max_points, bool) or not isinstance(
            self.cloud_max_points, int
        ):
            raise GraphStyleError("cloud_max_points must be a positive integer.")
        if self.cloud_max_points <= 0:
            raise GraphStyleError("cloud_max_points must be positive.")

    @property
    def resource_domain(self) -> str:
        return "density_rendering"

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "resource_domain": self.resource_domain,
            "browser_mesh_budget": self.browser_mesh_budget.to_json_dict(),
            "mesh_face_contract": self.mesh_face_contract.to_json_dict(),
            "cloud_max_points": self.cloud_max_points,
            "scientific_limits_present": False,
        }


__all__ = [
    "DENSITY_RENDERING_RESOURCE_POLICY_SCHEMA",
    "DensityRenderingResourcePolicy",
]
