"""Stage 11E-GR3 fixed-kernel scientific refinement tests."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis.density import ScientificDensityResourcePolicy
from mdstats.analysis.density.refinement import (
    BasinGridConvergenceCertificate,
    BasinGridPairComparison,
    CorridorGridPairComparison,
    DensityFieldLevelEvidence,
    GridConvergenceStatus,
    GridConvergenceStoppingPolicy,
    ScientificGridRefinementBundle,
    ScientificGridRefinementPolicy,
    FeatureGridCorrespondence,
    certify_basin_grid_convergence,
    certify_corridor_grid_convergence,
    certify_density_field_resolution,
    plan_scientific_grid_refinement,
    prepare_scientific_grid_refinement_bundle,
)
from mdstats.analysis.density.numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalSerializationError,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "mdstats" / "analysis" / "density" / "refinement.py"


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def cell() -> np.ndarray:
    return np.diag([4.0, 4.0, 4.0])


def resources(max_voxels: int = 100_000) -> ScientificDensityResourcePolicy:
    return ScientificDensityResourcePolicy(
        max_fields=8,
        max_total_voxels=max_voxels,
        max_samples=100_000,
        max_nonzero_nodes=max_voxels,
        max_stored_block_values=max_voxels,
        max_blocks=max_voxels,
        max_kernel_pairs=10_000_000,
        max_planning_bytes=64 * 1024**2,
        max_workspace_bytes=64 * 1024**2,
        max_cic_contributions=10_000_000,
        max_memory_bytes=128 * 1024**2,
        max_threads=2,
        max_wall_time_seconds=60.0,
        metadata={"test": "gr3"},
    )


def policy(resource: ScientificDensityResourcePolicy | None = None) -> ScientificGridRefinementPolicy:
    active = resources() if resource is None else resource
    return ScientificGridRefinementPolicy(
        fixed_kernel_covariance_cartesian=np.eye(3),
        fixed_kernel_signature=digest("kernel"),
        scientific_resource_policy_signature=active.signature,
        crossfit_partition_signature=digest("crossfit"),
        coarsest_interval=2.0,
        metadata={"domain": "discovery"},
    )


def ladder(active_policy: ScientificGridRefinementPolicy, resource: ScientificDensityResourcePolicy):
    return plan_scientific_grid_refinement(
        cell(), active_policy, resource_policy=resource
    )


def field_levels(active_policy, active_ladder, *, bad_last: bool = False):
    result = []
    zero = np.zeros((3, 3))
    for index, geometry in enumerate(active_ladder.levels):
        l1 = None if index == 0 else (0.03 if bad_last and index == len(active_ladder.levels) - 1 else 0.01)
        result.append(
            DensityFieldLevelEvidence(
                level_index=index,
                grid_shape=geometry.grid_shape,
                realized_intervals=geometry.realized_intervals,
                estimate_signature=digest(f"estimate-{index}"),
                fixed_kernel_signature=active_policy.fixed_kernel_signature,
                backend="dense" if index < 2 else "local_sparse",
                probability_normalization_residual=1.0e-8,
                number_normalization_residual=1.0e-8,
                probability_l1_change_from_previous=l1,
                probability_linf_change_from_previous=None if index == 0 else 0.02,
                cic_covariance_cartesian=zero,
                stencil_covariance_cartesian=zero,
                effective_artificial_covariance_cartesian=zero,
            )
        )
    return tuple(result)


def basin_pairs(active_ladder, *, ambiguous_last: bool = False):
    result = []
    for index in range(len(active_ladder.levels) - 1):
        result.append(
            BasinGridPairComparison(
                coarse_level_index=index,
                fine_level_index=index + 1,
                coarse_catalog_signature=digest(f"catalog-{index}"),
                fine_catalog_signature=digest(f"catalog-{index + 1}"),
                coarse_count=2,
                fine_count=2,
                correspondences=(
                    FeatureGridCorrespondence(0, 0, 0.1, 0.04, 0.98, 0.01),
                    FeatureGridCorrespondence(
                        1,
                        1,
                        0.1,
                        0.05,
                        0.97,
                        0.01,
                        ambiguous=ambiguous_last and index == len(active_ladder.levels) - 2,
                    ),
                ),
            )
        )
    return tuple(result)


def corridor_pairs(active_ladder, *, adjacency_fail_last: bool = False):
    return tuple(
        CorridorGridPairComparison(
            coarse_level_index=index,
            fine_level_index=index + 1,
            adjacency_equal=not (adjacency_fail_last and index == len(active_ladder.levels) - 2),
            minimum_overlap=0.95,
            maximum_bottleneck_displacement=0.05,
            maximum_relative_width_change=0.04,
            maximum_relative_density_change=0.03,
        )
        for index in range(len(active_ladder.levels) - 1)
    )


def test_stage11_grid_stopping_v1_exact_defaults_and_replay() -> None:
    stopping = GridConvergenceStoppingPolicy()
    assert stopping.policy_version == "stage11_grid_stopping_v1"
    assert stopping.refinement_factor == 2
    assert stopping.target_max_interval_to_sigma_min == 0.5
    assert stopping.consecutive_passing_level_pairs == 2
    assert stopping.maximum_basin_anchor_displacement_sigma == 0.10
    assert stopping.minimum_basin_overlap == 0.95
    assert stopping.maximum_basin_probability_change == 0.02
    assert stopping.minimum_corridor_overlap == 0.90
    assert stopping.maximum_bottleneck_displacement_sigma == 0.15
    assert stopping.maximum_corridor_relative_width_change == 0.10
    assert stopping.maximum_corridor_relative_density_change == 0.10
    assert GridConvergenceStoppingPolicy.from_json_dict(stopping.to_json_dict()).to_json_dict() == stopping.to_json_dict()


def test_scientific_planner_adds_post_gate_level_for_two_comparisons() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    assert active_policy.sigma_min == 1.0
    assert active_policy.physical_resolution_interval == 0.5
    assert active_policy.requested_finest_interval == 0.25
    assert [item.grid_shape for item in active_ladder.levels] == [
        (4, 4, 4),
        (8, 8, 8),
        (16, 16, 16),
    ]
    assert active_ladder.status.value == "target_reached"


def test_field_certificate_requires_two_consecutive_post_gate_passes() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    certificate = certify_density_field_resolution(
        active_ladder, active_policy, field_levels(active_policy, active_ladder)
    )
    assert certificate.status is GridConvergenceStatus.CONVERGED
    assert certificate.pair_physical_resolution_eligible == (True, True)
    assert certificate.consecutive_passing_pairs == 2
    assert certificate.accepted_level_index == 2
    restored = type(certificate).from_json_dict(certificate.to_json_dict())
    assert restored.to_json_dict() == certificate.to_json_dict()


def test_one_matching_post_gate_pair_is_diagnostic_only_when_budget_limited() -> None:
    resource = resources(max_voxels=8**3)
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    certificate = certify_density_field_resolution(
        active_ladder, active_policy, field_levels(active_policy, active_ladder)
    )
    assert active_ladder.status.value == "budget_limited"
    assert certificate.status is GridConvergenceStatus.UNRESOLVED_DUE_TO_RESOLUTION_BUDGET
    assert certificate.consecutive_passing_pairs == 1
    assert certificate.accepted_level_index is None


def test_field_metric_failure_does_not_promote_finest_level() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    certificate = certify_density_field_resolution(
        active_ladder,
        active_policy,
        field_levels(active_policy, active_ladder, bad_last=True),
    )
    assert certificate.status is GridConvergenceStatus.UNRESOLVED_DUE_TO_METRIC_FAILURE
    assert certificate.accepted_level_index is None


def test_fixed_kernel_change_fails_closed() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    levels = list(field_levels(active_policy, active_ladder))
    last = levels[-1]
    levels[-1] = DensityFieldLevelEvidence(
        level_index=last.level_index,
        grid_shape=last.grid_shape,
        realized_intervals=last.realized_intervals,
        estimate_signature=last.estimate_signature,
        fixed_kernel_signature=digest("changed-kernel"),
        backend=last.backend,
        probability_normalization_residual=last.probability_normalization_residual,
        number_normalization_residual=last.number_normalization_residual,
        probability_l1_change_from_previous=last.probability_l1_change_from_previous,
        probability_linf_change_from_previous=last.probability_linf_change_from_previous,
        cic_covariance_cartesian=last.cic_covariance_cartesian,
        stencil_covariance_cartesian=last.stencil_covariance_cartesian,
        effective_artificial_covariance_cartesian=last.effective_artificial_covariance_cartesian,
    )
    with pytest.raises(DensityNumericalInputError, match="kernel change"):
        certify_density_field_resolution(active_ladder, active_policy, levels)


def test_basin_can_converge_while_corridor_remains_unresolved() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    basin = certify_basin_grid_convergence(
        active_ladder, active_policy, basin_pairs(active_ladder)
    )
    corridor = certify_corridor_grid_convergence(active_ladder, active_policy, ())
    assert basin.status is GridConvergenceStatus.CONVERGED
    assert corridor.status is GridConvergenceStatus.UNRESOLVED_DUE_TO_MISSING_EVIDENCE
    assert corridor.reason_codes == ("corridor_width_or_support_evidence_unavailable",)


def test_basin_ambiguity_breaks_consecutive_passes() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    basin = certify_basin_grid_convergence(
        active_ladder,
        active_policy,
        basin_pairs(active_ladder, ambiguous_last=True),
    )
    assert basin.status is GridConvergenceStatus.UNRESOLVED_DUE_TO_METRIC_FAILURE
    assert basin.consecutive_passing_pairs == 0


def test_corridor_certificate_is_independent_and_can_converge() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    corridor = certify_corridor_grid_convergence(
        active_ladder, active_policy, corridor_pairs(active_ladder)
    )
    assert corridor.status is GridConvergenceStatus.CONVERGED
    failed = certify_corridor_grid_convergence(
        active_ladder,
        active_policy,
        corridor_pairs(active_ladder, adjacency_fail_last=True),
    )
    assert failed.status is GridConvergenceStatus.UNRESOLVED_DUE_TO_METRIC_FAILURE


def test_bundle_replay_and_tamper_rejection() -> None:
    resource = resources()
    active_policy = policy(resource)
    active_ladder = ladder(active_policy, resource)
    bundle = prepare_scientific_grid_refinement_bundle(
        active_ladder,
        active_policy,
        field_level_evidence=field_levels(active_policy, active_ladder),
        basin_pair_comparisons=basin_pairs(active_ladder),
        corridor_pair_comparisons=(),
    )
    assert bundle.field_certificate.status is GridConvergenceStatus.CONVERGED
    assert bundle.basin_certificate.status is GridConvergenceStatus.CONVERGED
    assert bundle.corridor_certificate.status is GridConvergenceStatus.UNRESOLVED_DUE_TO_MISSING_EVIDENCE
    restored = ScientificGridRefinementBundle.from_json_dict(bundle.to_json_dict())
    assert restored.to_json_dict() == bundle.to_json_dict()
    tampered = bundle.to_json_dict()
    tampered["policy"]["coarsest_interval"] = 1.5
    with pytest.raises(DensityNumericalSerializationError, match="signature mismatch"):
        ScientificGridRefinementBundle.from_json_dict(tampered)


def test_resource_signature_mismatch_fails_before_planning() -> None:
    first = resources()
    second = resources(max_voxels=200_000)
    active_policy = policy(first)
    with pytest.raises(DensityNumericalInputError, match="resource signature"):
        plan_scientific_grid_refinement(cell(), active_policy, resource_policy=second)


def test_analysis_refinement_module_imports_no_plotting_or_rendering_policy() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("plotting" in item for item in imports)
    text = MODULE.read_text(encoding="utf-8")
    for forbidden in ("Plotly", "Mesh3d", "browser budget", "HTML artifact"):
        assert forbidden not in text
