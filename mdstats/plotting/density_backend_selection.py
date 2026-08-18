"""Transactional automatic backend selection for periodic density fields.

Architecture gate LD4 compares exact dense and local-sparse Phase-B estimates
before any scalar field is allocated.  The selection policy is project-specific:
broad fields prefer dense storage, strongly localized fields prefer sparse storage
when it also provides a substantial peak-memory reduction, and intermediate cases
use deterministic peak-memory/work tie breaking.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import product
from math import ceil, log2
from typing import Any, Mapping, Sequence


from .density_contracts import (
    AUTO_BACKEND,
    DENSE_BACKEND,
    LOCAL_SPARSE_BACKEND,
    FrozenJSONMapping,
    freeze_json_mapping,
)
from .density_planning import (
    DensityPhaseAFieldPlan,
    DensityPhaseBFieldPlan,
    DensityPlanningLimits,
    DensityScenePlan,
    plan_density_scene,
)
from .graph_errors import GraphAdapterError, GraphComplexityError

DENSITY_BACKEND_CANDIDATE_SCHEMA = "mdstats.density-backend-candidate.v1"
DENSITY_BACKEND_SELECTION_SCHEMA = "mdstats.density-backend-selection.v1"
DENSITY_AUTO_POLICY = "mdstats.auto-density-backend.v1"
AUTO_DENSE_ACTIVE_FRACTION = 0.50
AUTO_SPARSE_PEAK_RATIO = 0.70


@dataclass(frozen=True, slots=True)
class DensityBackendCandidateEstimate:
    """One exact Phase-B backend estimate and its feasibility state."""

    backend: str
    feasible: bool
    logical_node_count: int
    active_node_count: int
    stored_value_count: int
    stored_block_count: int
    kernel_pair_count: int
    planning_bytes: int
    retained_bytes: int
    estimated_peak_bytes: int
    estimated_work: int
    infeasible_reason: str | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = DENSITY_BACKEND_CANDIDATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_BACKEND_CANDIDATE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported backend-candidate schema {self.schema_version!r}."
            )
        if self.backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND}:
            raise GraphAdapterError("Backend candidate must be dense or local_sparse.")
        for name in (
            "logical_node_count",
            "active_node_count",
            "stored_value_count",
            "stored_block_count",
            "kernel_pair_count",
            "planning_bytes",
            "retained_bytes",
            "estimated_peak_bytes",
            "estimated_work",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        if self.active_node_count > self.logical_node_count:
            raise GraphAdapterError("active_node_count exceeds logical_node_count.")
        if self.feasible and self.infeasible_reason is not None:
            raise GraphAdapterError("A feasible candidate cannot have an infeasible reason.")
        if not self.feasible and not self.infeasible_reason:
            raise GraphAdapterError("An infeasible candidate requires a reason.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def active_fraction(self) -> float:
        if self.logical_node_count == 0:
            return 0.0
        return self.active_node_count / self.logical_node_count

    @property
    def stored_fraction(self) -> float:
        if self.logical_node_count == 0:
            return 0.0
        return self.stored_value_count / self.logical_node_count

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "backend": self.backend,
            "feasible": self.feasible,
            "logical_node_count": self.logical_node_count,
            "active_node_count": self.active_node_count,
            "active_fraction": self.active_fraction,
            "stored_value_count": self.stored_value_count,
            "stored_fraction": self.stored_fraction,
            "stored_block_count": self.stored_block_count,
            "kernel_pair_count": self.kernel_pair_count,
            "planning_bytes": self.planning_bytes,
            "retained_bytes": self.retained_bytes,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "estimated_work": self.estimated_work,
            "infeasible_reason": self.infeasible_reason,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(
        cls, value: Mapping[str, Any]
    ) -> "DensityBackendCandidateEstimate":
        """Reconstruct a candidate estimate from canonical JSON data."""

        return cls(
            schema_version=str(value.get("schema_version", "")),
            backend=str(value.get("backend", "")),
            feasible=bool(value.get("feasible", False)),
            logical_node_count=int(value.get("logical_node_count", 0)),
            active_node_count=int(value.get("active_node_count", 0)),
            stored_value_count=int(value.get("stored_value_count", 0)),
            stored_block_count=int(value.get("stored_block_count", 0)),
            kernel_pair_count=int(value.get("kernel_pair_count", 0)),
            planning_bytes=int(value.get("planning_bytes", 0)),
            retained_bytes=int(value.get("retained_bytes", 0)),
            estimated_peak_bytes=int(value.get("estimated_peak_bytes", 0)),
            estimated_work=int(value.get("estimated_work", 0)),
            infeasible_reason=(
                None
                if value.get("infeasible_reason") is None
                else str(value.get("infeasible_reason"))
            ),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityBackendSelection:
    """Serializable outcome of the LD4 backend policy for one field."""

    field_key: str
    requested_backend: str
    selected_backend: str
    reason: str
    dense: DensityBackendCandidateEstimate
    local_sparse: DensityBackendCandidateEstimate
    policy: str = DENSITY_AUTO_POLICY
    globally_overridden: bool = False
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = DENSITY_BACKEND_SELECTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_BACKEND_SELECTION_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported backend-selection schema {self.schema_version!r}."
            )
        if not self.field_key:
            raise GraphAdapterError("field_key must be nonempty.")
        if self.requested_backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND, AUTO_BACKEND}:
            raise GraphAdapterError("Invalid requested backend.")
        if self.selected_backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND}:
            raise GraphAdapterError("Invalid selected backend.")
        if not self.reason:
            raise GraphAdapterError("Backend selection requires a reason.")
        chosen = self.dense if self.selected_backend == DENSE_BACKEND else self.local_sparse
        if not chosen.feasible:
            raise GraphAdapterError("The selected density backend must be feasible.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def selected(self) -> DensityBackendCandidateEstimate:
        return self.dense if self.selected_backend == DENSE_BACKEND else self.local_sparse

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "requested_backend": self.requested_backend,
            "selected_backend": self.selected_backend,
            "reason": self.reason,
            "policy": self.policy,
            "globally_overridden": self.globally_overridden,
            "dense": self.dense.to_json_dict(),
            "local_sparse": self.local_sparse.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(
        cls, value: Mapping[str, Any]
    ) -> "DensityBackendSelection":
        """Reconstruct a backend decision from canonical JSON data."""

        dense = value.get("dense")
        sparse = value.get("local_sparse")
        if not isinstance(dense, Mapping) or not isinstance(sparse, Mapping):
            raise GraphAdapterError(
                "Serialized backend selection requires dense and local_sparse records."
            )
        return cls(
            schema_version=str(value.get("schema_version", "")),
            field_key=str(value.get("field_key", "")),
            requested_backend=str(value.get("requested_backend", "")),
            selected_backend=str(value.get("selected_backend", "")),
            reason=str(value.get("reason", "")),
            dense=DensityBackendCandidateEstimate.from_json_dict(dense),
            local_sparse=DensityBackendCandidateEstimate.from_json_dict(sparse),
            policy=str(value.get("policy", DENSITY_AUTO_POLICY)),
            globally_overridden=bool(value.get("globally_overridden", False)),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityBackendCandidateSet:
    """The dense and sparse Phase-B plans considered for one field."""

    field_key: str
    requested_backend: str
    dense_plan: DensityPhaseBFieldPlan | None
    sparse_plan: DensityPhaseBFieldPlan | None
    dense_estimate: DensityBackendCandidateEstimate
    sparse_estimate: DensityBackendCandidateEstimate
    preferred_backend: str
    preferred_reason: str
    sparse_activation_fraction: float

    def __post_init__(self) -> None:
        if self.requested_backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND, AUTO_BACKEND}:
            raise GraphAdapterError("Invalid requested backend.")
        if self.preferred_backend not in {DENSE_BACKEND, LOCAL_SPARSE_BACKEND}:
            raise GraphAdapterError("Invalid preferred backend.")

    def plan_for(self, backend: str) -> DensityPhaseBFieldPlan:
        plan = self.dense_plan if backend == DENSE_BACKEND else self.sparse_plan
        if plan is None:
            raise GraphComplexityError(
                f"Backend {backend!r} is unavailable for {self.field_key!r}."
            )
        return plan

    def estimate_for(self, backend: str) -> DensityBackendCandidateEstimate:
        return self.dense_estimate if backend == DENSE_BACKEND else self.sparse_estimate


def _plan_infeasible_reason(
    plan: DensityPhaseBFieldPlan,
    limits: DensityPlanningLimits,
) -> str | None:
    backend = str(plan.metadata.get("backend", DENSE_BACKEND))
    checks: list[tuple[int, int, str]] = [
        (plan.sample_count, limits.max_density_samples, "max_density_samples"),
        (plan.sample_bytes, limits.max_density_sample_bytes, "max_density_sample_bytes"),
        (plan.planning_bytes, limits.max_density_planning_bytes, "max_density_planning_bytes"),
        (plan.stencil_value_count, limits.max_density_stencil_values, "max_density_stencil_values"),
        (plan.nonzero_node_count_upper, limits.max_density_nonzero_nodes, "max_density_nonzero_nodes"),
        (plan.stored_value_count, limits.max_density_stored_block_values, "max_density_stored_block_values"),
        (plan.stored_block_count, limits.max_density_blocks, "max_density_blocks"),
        (plan.kernel_pair_count, limits.max_density_kernel_pairs, "max_density_kernel_pairs"),
        (plan.component_value_count, limits.max_density_component_values, "max_density_component_values"),
        (plan.mesh_cell_count, limits.max_density_mesh_cells, "max_density_mesh_cells"),
        (plan.mesh_face_count_upper, limits.max_density_mesh_faces, "max_density_mesh_faces"),
        (plan.render_point_count_upper, limits.max_density_render_points, "max_density_render_points"),
    ]
    if backend == DENSE_BACKEND:
        checks.append((plan.logical_node_count, limits.max_density_voxels, "max_density_voxels"))
    peak = max(plan.transient_bytes_upper, plan.planning_bytes + plan.retained_bytes)
    checks.append((peak, limits.max_density_total_peak_bytes, "max_density_total_peak_bytes"))
    for value, limit, name in checks:
        if value > limit:
            return f"{name}:{value}>{limit}"
    return None


def estimate_backend_candidate(
    plan: DensityPhaseBFieldPlan | None,
    *,
    backend: str,
    limits: DensityPlanningLimits,
    infeasible_reason: str | None = None,
) -> DensityBackendCandidateEstimate:
    """Build one deterministic estimate from an exact Phase-B plan."""

    if plan is None:
        return DensityBackendCandidateEstimate(
            backend=backend,
            feasible=False,
            logical_node_count=0,
            active_node_count=0,
            stored_value_count=0,
            stored_block_count=0,
            kernel_pair_count=0,
            planning_bytes=0,
            retained_bytes=0,
            estimated_peak_bytes=0,
            estimated_work=0,
            infeasible_reason=infeasible_reason or "candidate_planning_failed",
        )
    reason = infeasible_reason or _plan_infeasible_reason(plan, limits)
    logical = plan.logical_node_count
    active = plan.nonzero_node_count_upper
    peak = max(plan.transient_bytes_upper, plan.planning_bytes + plan.retained_bytes)
    cic_work = 8 * plan.sample_count
    if backend == DENSE_BACKEND:
        fft_stages = max(1, ceil(log2(max(2, logical))))
        work = cic_work + logical * fft_stages + logical
    elif str(plan.metadata.get("phase_b_execution_planner", "")) == "ld8_s3_hybrid_exact_v1":
        # Convert the calibrated mixed direct/FFT wall estimate into one stable
        # work-equivalent scalar for deterministic backend tie breaking.  The
        # scene planner uses the wall estimate itself for admission.
        hybrid_seconds = float(plan.metadata.get("hybrid_estimated_wall_seconds", 0.0))
        work = (
            cic_work
            + int(hybrid_seconds * limits.time_model.kernel_pairs_per_second)
            + plan.stored_value_count
        )
    else:
        work = cic_work + plan.kernel_pair_count + plan.stored_value_count
    candidate_metadata = {
        "phase_b_schema": plan.schema_version,
        "phase_b_execution_planner": str(
            plan.metadata.get("phase_b_execution_planner", "unspecified")
        ),
        "kernel_pair_semantics": str(
            plan.metadata.get("kernel_pair_semantics", "unspecified")
        ),
        "exact_contribution_count": int(
            plan.metadata.get("exact_contribution_count", plan.kernel_pair_count)
        ),
        "direct_pair_count": int(
            plan.metadata.get("direct_pair_count", plan.kernel_pair_count)
        ),
        "hybrid_estimated_wall_seconds": float(
            plan.metadata.get("hybrid_estimated_wall_seconds", 0.0)
        ),
    }
    return DensityBackendCandidateEstimate(
        backend=backend,
        feasible=reason is None,
        logical_node_count=logical,
        active_node_count=active,
        stored_value_count=plan.stored_value_count,
        stored_block_count=plan.stored_block_count,
        kernel_pair_count=plan.kernel_pair_count,
        planning_bytes=plan.planning_bytes,
        retained_bytes=plan.retained_bytes,
        estimated_peak_bytes=peak,
        estimated_work=int(work),
        infeasible_reason=reason,
        metadata=candidate_metadata,
    )


def preferred_auto_backend(
    dense: DensityBackendCandidateEstimate,
    sparse: DensityBackendCandidateEstimate,
    *,
    sparse_activation_fraction: float,
) -> tuple[str, str]:
    """Apply the normative LD4 field-local policy anchors."""

    if not dense.feasible and not sparse.feasible:
        raise GraphComplexityError(
            "Neither dense nor local_sparse is feasible: "
            f"dense={dense.infeasible_reason}; sparse={sparse.infeasible_reason}."
        )
    if dense.feasible and not sparse.feasible:
        return DENSE_BACKEND, "sparse_infeasible"
    if sparse.feasible and not dense.feasible:
        return LOCAL_SPARSE_BACKEND, "dense_infeasible"

    active = sparse.active_fraction
    if active >= AUTO_DENSE_ACTIVE_FRACTION:
        return DENSE_BACKEND, "broad_active_fraction"
    if (
        active <= float(sparse_activation_fraction)
        and sparse.estimated_peak_bytes
        <= AUTO_SPARSE_PEAK_RATIO * dense.estimated_peak_bytes
    ):
        return LOCAL_SPARSE_BACKEND, "localized_and_memory_efficient"
    if sparse.estimated_peak_bytes < dense.estimated_peak_bytes:
        return LOCAL_SPARSE_BACKEND, "lower_estimated_peak_bytes"
    if dense.estimated_peak_bytes < sparse.estimated_peak_bytes:
        return DENSE_BACKEND, "lower_estimated_peak_bytes"
    if sparse.estimated_work < dense.estimated_work:
        return LOCAL_SPARSE_BACKEND, "lower_estimated_work"
    if dense.estimated_work < sparse.estimated_work:
        return DENSE_BACKEND, "lower_estimated_work"
    return DENSE_BACKEND, "dense_tie_break"


def make_candidate_set(
    *,
    field_key: str,
    requested_backend: str,
    dense_plan: DensityPhaseBFieldPlan | None,
    sparse_plan: DensityPhaseBFieldPlan | None,
    limits: DensityPlanningLimits,
    sparse_activation_fraction: float,
    dense_error: str | None = None,
    sparse_error: str | None = None,
) -> DensityBackendCandidateSet:
    dense = estimate_backend_candidate(
        dense_plan, backend=DENSE_BACKEND, limits=limits, infeasible_reason=dense_error
    )
    sparse = estimate_backend_candidate(
        sparse_plan,
        backend=LOCAL_SPARSE_BACKEND,
        limits=limits,
        infeasible_reason=sparse_error,
    )
    if requested_backend == DENSE_BACKEND:
        if not dense.feasible:
            raise GraphComplexityError(
                f"Forced dense backend for {field_key!r} is infeasible: {dense.infeasible_reason}."
            )
        preferred, reason = DENSE_BACKEND, "forced_dense"
    elif requested_backend == LOCAL_SPARSE_BACKEND:
        if not sparse.feasible:
            raise GraphComplexityError(
                f"Forced local_sparse backend for {field_key!r} is infeasible: "
                f"{sparse.infeasible_reason}."
            )
        preferred, reason = LOCAL_SPARSE_BACKEND, "forced_local_sparse"
    else:
        preferred, reason = preferred_auto_backend(
            dense,
            sparse,
            sparse_activation_fraction=sparse_activation_fraction,
        )
    return DensityBackendCandidateSet(
        field_key=field_key,
        requested_backend=requested_backend,
        dense_plan=dense_plan,
        sparse_plan=sparse_plan,
        dense_estimate=dense,
        sparse_estimate=sparse,
        preferred_backend=preferred,
        preferred_reason=reason,
        sparse_activation_fraction=float(sparse_activation_fraction),
    )


def _selection_for(
    candidate: DensityBackendCandidateSet,
    selected_backend: str,
    *,
    globally_overridden: bool,
) -> DensityBackendSelection:
    reason = candidate.preferred_reason
    if globally_overridden:
        reason = f"global_resource_override_from_{candidate.preferred_backend}"
    return DensityBackendSelection(
        field_key=candidate.field_key,
        requested_backend=candidate.requested_backend,
        selected_backend=selected_backend,
        reason=reason,
        dense=candidate.dense_estimate,
        local_sparse=candidate.sparse_estimate,
        globally_overridden=globally_overridden,
        metadata={
            "dense_active_fraction_reference": candidate.dense_estimate.active_fraction,
            "sparse_active_fraction": candidate.sparse_estimate.active_fraction,
            "dense_anchor_fraction": AUTO_DENSE_ACTIVE_FRACTION,
            "sparse_anchor_fraction": candidate.sparse_activation_fraction,
            "sparse_peak_ratio_anchor": AUTO_SPARSE_PEAK_RATIO,
        },
    )


def _plan_with_selection(
    plan: DensityPhaseBFieldPlan,
    selection: DensityBackendSelection,
) -> DensityPhaseBFieldPlan:
    metadata = plan.metadata.to_json_dict()
    metadata["backend"] = selection.selected_backend
    metadata["backend_selection"] = selection.to_json_dict()
    return replace(plan, metadata=metadata)


def select_density_scene_backends(
    *,
    phase_a_fields: Sequence[DensityPhaseAFieldPlan],
    candidates: Sequence[DensityBackendCandidateSet],
    limits: DensityPlanningLimits,
    metadata: Mapping[str, Any] | None = None,
    planner: Any = plan_density_scene,
) -> DensityScenePlan:
    """Select one globally feasible deterministic backend combination."""

    candidate_tuple = tuple(candidates)
    if tuple(v.field_key for v in candidate_tuple) != tuple(
        v.field_key for v in phase_a_fields
    ):
        raise GraphAdapterError("Phase-A and backend-candidate field orders differ.")
    choices: list[tuple[str, ...]] = []
    for item in candidate_tuple:
        available: list[str] = []
        if item.dense_plan is not None and item.dense_estimate.feasible:
            available.append(DENSE_BACKEND)
        if item.sparse_plan is not None and item.sparse_estimate.feasible:
            available.append(LOCAL_SPARSE_BACKEND)
        if not available:
            raise GraphComplexityError(
                f"No feasible backend remains for {item.field_key!r}."
            )
        choices.append(tuple(available))

    feasible: list[tuple[tuple[int, int, int, int], DensityScenePlan, tuple[str, ...]]] = []
    failures: list[str] = []
    for selected_backends in product(*choices):
        plans: list[DensityPhaseBFieldPlan] = []
        work = 0
        sparse_count = 0
        violations = 0
        for item, backend in zip(candidate_tuple, selected_backends, strict=True):
            overridden = backend != item.preferred_backend
            violations += int(overridden)
            sparse_count += int(backend == LOCAL_SPARSE_BACKEND)
            selection = _selection_for(
                item, backend, globally_overridden=overridden
            )
            plans.append(_plan_with_selection(item.plan_for(backend), selection))
            work += item.estimate_for(backend).estimated_work
        try:
            scene = planner(
                phase_a_fields=phase_a_fields,
                phase_b_fields=plans,
                limits=limits,
                metadata={
                    "backend_selection_policy": DENSITY_AUTO_POLICY,
                    "selected_backends": list(selected_backends),
                    **({} if metadata is None else dict(metadata)),
                },
            )
        except GraphComplexityError as exc:
            failures.append(f"{selected_backends}: {exc}")
            continue
        score = (violations, scene.estimated_peak_bytes, work, sparse_count)
        feasible.append((score, scene, tuple(selected_backends)))
    if not feasible:
        detail = "; ".join(failures[:8])
        raise GraphComplexityError(
            "No globally feasible density backend combination exists. " + detail
        )
    feasible.sort(key=lambda item: (item[0], item[2]))
    return feasible[0][1]
