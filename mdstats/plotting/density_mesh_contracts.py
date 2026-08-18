"""Explicit face-count contracts for density mesh extraction and display.

The contract separates three quantities that were historically overloaded as
``max_mesh_faces``:

``raw_extraction_face_limit``
    A computational safety limit for marching-cubes output before optional
    simplification.  Runtime-derived resource limits remain authoritative.

``visual_target_faces``
    A soft scene-fitting target.  Exceeding it is not an error; the scene
    fitting controller may retry or reallocate in a later stage.

``standalone_final_face_limit``
    An optional terminal limit used by standalone mesh APIs.  Scene-owned
    rendering sets this to ``None`` so a target miss reaches the fitting
    controller instead of raising prematurely.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal

import numpy as np

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphStyleError

DENSITY_MESH_FACE_CONTRACT_SCHEMA = "mdstats.density-mesh-face-contract.v1"
DENSITY_MESH_FACE_REPORT_SCHEMA = "mdstats.density-mesh-face-report.v1"
DEFAULT_STANDALONE_FINAL_MESH_FACES = 250_000


def _optional_positive_int(value: Any, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer or None.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be a positive integer or None.")
    return result


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a nonnegative integer.")
    result = int(value)
    if result < 0:
        raise GraphStyleError(f"{name} must be a nonnegative integer.")
    return result


@dataclass(frozen=True, slots=True)
class DensityMeshFaceContract:
    """Face-count contract for one density shell.

    ``mode='standalone'`` preserves the historical terminal face limit.
    ``mode='scene_controller'`` requires a visual target and forbids a terminal
    shell limit so the later closed-loop scene fitter owns final compliance.
    """

    raw_extraction_face_limit: int | None = None
    visual_target_faces: int | None = None
    standalone_final_face_limit: int | None = DEFAULT_STANDALONE_FINAL_MESH_FACES
    mode: Literal["standalone", "scene_controller"] = "standalone"
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_MESH_FACE_CONTRACT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_MESH_FACE_CONTRACT_SCHEMA:
            raise GraphAdapterError("Unsupported density-mesh-face-contract schema.")
        if self.mode not in {"standalone", "scene_controller"}:
            raise GraphStyleError("mode must be standalone or scene_controller.")
        raw = _optional_positive_int(
            self.raw_extraction_face_limit,
            name="raw_extraction_face_limit",
        )
        target = _optional_positive_int(
            self.visual_target_faces,
            name="visual_target_faces",
        )
        final = _optional_positive_int(
            self.standalone_final_face_limit,
            name="standalone_final_face_limit",
        )
        if self.mode == "scene_controller":
            if target is None:
                raise GraphStyleError(
                    "scene_controller mode requires visual_target_faces."
                )
            if final is not None:
                raise GraphStyleError(
                    "scene_controller mode requires standalone_final_face_limit=None."
                )
        object.__setattr__(self, "raw_extraction_face_limit", raw)
        object.__setattr__(self, "visual_target_faces", target)
        object.__setattr__(self, "standalone_final_face_limit", final)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @classmethod
    def standalone(
        cls,
        *,
        final_face_limit: int = DEFAULT_STANDALONE_FINAL_MESH_FACES,
        raw_extraction_face_limit: int | None = None,
        visual_target_faces: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "DensityMeshFaceContract":
        final = _optional_positive_int(final_face_limit, name="final_face_limit")
        assert final is not None
        return cls(
            raw_extraction_face_limit=raw_extraction_face_limit,
            visual_target_faces=(
                final if visual_target_faces is None else visual_target_faces
            ),
            standalone_final_face_limit=final,
            mode="standalone",
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def scene_controller(
        cls,
        *,
        raw_extraction_face_limit: int,
        visual_target_faces: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> "DensityMeshFaceContract":
        return cls(
            raw_extraction_face_limit=raw_extraction_face_limit,
            visual_target_faces=visual_target_faces,
            standalone_final_face_limit=None,
            mode="scene_controller",
            metadata={} if metadata is None else metadata,
        )

    def resolve_raw_limit(self, runtime_raw_face_limit: int) -> "DensityMeshFaceContract":
        """Return a copy capped by the authoritative runtime raw limit."""

        runtime = _optional_positive_int(
            runtime_raw_face_limit,
            name="runtime_raw_face_limit",
        )
        assert runtime is not None
        resolved = (
            runtime
            if self.raw_extraction_face_limit is None
            else min(runtime, self.raw_extraction_face_limit)
        )
        return replace(self, raw_extraction_face_limit=resolved)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "raw_extraction_face_limit": self.raw_extraction_face_limit,
            "visual_target_faces": self.visual_target_faces,
            "standalone_final_face_limit": self.standalone_final_face_limit,
            "mode": self.mode,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityMeshFaceContract":
        return cls(
            schema_version=str(value["schema_version"]),
            raw_extraction_face_limit=value.get("raw_extraction_face_limit"),
            visual_target_faces=value.get("visual_target_faces"),
            standalone_final_face_limit=value.get("standalone_final_face_limit"),
            mode=str(value.get("mode", "standalone")),  # type: ignore[arg-type]
            metadata=value.get("metadata", {}),
        )



@dataclass(frozen=True, slots=True)
class DensityMeshFaceReport:
    """Observed final shell count against one explicit face contract."""

    final_face_count: int
    contract: DensityMeshFaceContract
    visual_target_met: bool | None
    visual_target_overage_faces: int
    standalone_final_limit_met: bool | None
    schema_version: str = DENSITY_MESH_FACE_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_MESH_FACE_REPORT_SCHEMA:
            raise GraphAdapterError("Unsupported density-mesh-face-report schema.")
        count = _nonnegative_int(self.final_face_count, name="final_face_count")
        if not isinstance(self.contract, DensityMeshFaceContract):
            raise TypeError("contract must be DensityMeshFaceContract.")
        expected_target_met = (
            None
            if self.contract.visual_target_faces is None
            else count <= self.contract.visual_target_faces
        )
        expected_overage = (
            0
            if self.contract.visual_target_faces is None
            else max(0, count - self.contract.visual_target_faces)
        )
        expected_final_met = (
            None
            if self.contract.standalone_final_face_limit is None
            else count <= self.contract.standalone_final_face_limit
        )
        if self.visual_target_met is not expected_target_met:
            raise GraphAdapterError("visual_target_met is inconsistent.")
        if int(self.visual_target_overage_faces) != expected_overage:
            raise GraphAdapterError("visual_target_overage_faces is inconsistent.")
        if self.standalone_final_limit_met is not expected_final_met:
            raise GraphAdapterError("standalone_final_limit_met is inconsistent.")
        object.__setattr__(self, "final_face_count", count)
        object.__setattr__(self, "visual_target_overage_faces", expected_overage)

    @property
    def requires_scene_refit(self) -> bool:
        return self.visual_target_met is False

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "final_face_count": self.final_face_count,
            "contract": self.contract.to_json_dict(),
            "visual_target_met": self.visual_target_met,
            "visual_target_overage_faces": self.visual_target_overage_faces,
            "standalone_final_limit_met": self.standalone_final_limit_met,
            "requires_scene_refit": self.requires_scene_refit,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityMeshFaceReport":
        return cls(
            schema_version=str(value["schema_version"]),
            final_face_count=int(value["final_face_count"]),
            contract=DensityMeshFaceContract.from_json_dict(value["contract"]),
            visual_target_met=value.get("visual_target_met"),
            visual_target_overage_faces=int(value["visual_target_overage_faces"]),
            standalone_final_limit_met=value.get("standalone_final_limit_met"),
        )


def evaluate_density_mesh_face_contract(
    final_face_count: int,
    contract: DensityMeshFaceContract,
) -> DensityMeshFaceReport:
    """Evaluate a final shell count without conflating a target miss with failure."""

    count = _nonnegative_int(final_face_count, name="final_face_count")
    if not isinstance(contract, DensityMeshFaceContract):
        raise TypeError("contract must be DensityMeshFaceContract.")
    target_met = (
        None
        if contract.visual_target_faces is None
        else count <= contract.visual_target_faces
    )
    final_met = (
        None
        if contract.standalone_final_face_limit is None
        else count <= contract.standalone_final_face_limit
    )
    return DensityMeshFaceReport(
        final_face_count=count,
        contract=contract,
        visual_target_met=target_met,
        visual_target_overage_faces=(
            0
            if contract.visual_target_faces is None
            else max(0, count - contract.visual_target_faces)
        ),
        standalone_final_limit_met=final_met,
    )

def legacy_standalone_face_contract(
    *,
    max_faces: int | None,
    max_raw_faces: int | None,
) -> DensityMeshFaceContract:
    """Translate the historical standalone arguments into the explicit contract."""

    final = (
        DEFAULT_STANDALONE_FINAL_MESH_FACES
        if max_faces is None
        else _optional_positive_int(max_faces, name="max_faces")
    )
    assert final is not None
    raw = _optional_positive_int(max_raw_faces, name="max_raw_faces")
    return DensityMeshFaceContract.standalone(
        final_face_limit=final,
        raw_extraction_face_limit=raw,
        visual_target_faces=final,
        metadata={"compatibility_source": "legacy_max_faces"},
    )
