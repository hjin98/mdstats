from __future__ import annotations

import copy
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import (
    AssignmentConflictStatus,
    CenterModelKind,
    CrossingDriveStatus,
    EvidenceBlockPlan,
    FrameworkPredictorTable,
    FrozenRegionDefinition,
    GeometryConditionedSiteCatalog,
    GeometryConditioningInputError,
    GeometryConditioningOptions,
    GeometryConditioningResourceError,
    GeometryConditioningResourcePolicy,
    GeometryModelDecision,
    RegionMembership,
    analyze_geometry_conditioned_state_samples,
    prepare_geometry_conditioned_site_catalog,
)
from mdstats.analysis.density.coordination_fingerprints import (
    CoordinationFingerprintCatalog,
    CoordinationFingerprintOptions,
    CoordinationFingerprintResourcePolicy,
)

from tests.test_stage11e5a_coordination_fingerprints import _result


VIEW = "e" * 64
VALIDATED = "d" * 64


def _inputs(local, predictors, *, state=0, candidate=0, identity=None, frames=None, ions=None, segments=None,
            core=0.12, basin=0.35, options=None):
    local = np.asarray(local, dtype=float)
    predictors = np.asarray(predictors, dtype=float)
    n = len(local)
    identity = identity or f"ring:state-{state}"
    fingerprint = _result(local)
    if frames is None:
        frames = np.arange(n)
    if ions is None:
        ions = np.zeros(n, dtype=int)
    fingerprint = replace(
        fingerprint,
        state_id=state,
        candidate_index=candidate,
        persistent_identity=identity,
        sample_indices=np.arange(n, dtype=int),
        frame_indices=np.asarray(frames, dtype=int),
        ion_atom_indices=np.asarray(ions, dtype=int),
        signature="",
    )
    if segments is None:
        segments = np.zeros(n, dtype=int)
    table = FrameworkPredictorTable(
        state,
        candidate,
        identity,
        fingerprint.sample_indices,
        fingerprint.frame_indices,
        np.asarray(segments, dtype=int),
        tuple(f"framework_feature_{i}" for i in range(predictors.shape[1])),
        predictors,
        VIEW,
    )
    region = FrozenRegionDefinition(state, candidate, identity, (0.0, 0.0, 0.0), core, basin, VALIDATED)
    plan = EvidenceBlockPlan(tuple(range(0, 20)), tuple(range(20, 40)), tuple(range(40, 60)))
    return fingerprint, table, region, plan, options


def test_dynamic_framework_model_is_retained_only_after_selection_and_validation():
    rng = np.random.default_rng(30)
    x = np.linspace(-1.0, 1.0, 60)[:, None]
    local = np.column_stack((0.42 * x[:, 0], -0.16 * x[:, 0], np.zeros(60)))
    local += rng.normal(scale=0.008, size=local.shape)
    fingerprint, table, region, plan, _ = _inputs(local, x, core=0.10, basin=0.45)
    result = analyze_geometry_conditioned_state_samples(
        fingerprint=fingerprint,
        predictor_table=table,
        frozen_region=region,
        block_plan=plan,
    )
    assert result.decision is GeometryModelDecision.DYNAMIC_RETAINED
    assert result.selected_model_kind is CenterModelKind.AFFINE_FRAMEWORK
    assert result.block_scores[1].relative_improvement > 0.8
    assert result.block_scores[2].dynamic_rms < result.block_scores[2].static_rms
    assert np.trace(result.dynamic_residual_covariance) < np.trace(result.static_residual_covariance)
    assert "frozen_discovery_assignments_not_recomputed" in result.diagnostics


def test_final_validation_can_contradict_selection_gain_and_retain_static_model():
    rng = np.random.default_rng(31)
    x = np.linspace(-1.0, 1.0, 60)[:, None]
    local = np.zeros((60, 3))
    local[:40, 0] = 0.45 * x[:40, 0]
    local[40:, 0] = -0.45 * x[40:, 0]
    local += rng.normal(scale=0.004, size=local.shape)
    fingerprint, table, region, plan, _ = _inputs(local, x, core=0.10, basin=0.50)
    result = analyze_geometry_conditioned_state_samples(
        fingerprint=fingerprint,
        predictor_table=table,
        frozen_region=region,
        block_plan=plan,
    )
    assert result.block_scores[1].relative_improvement > 0.5
    assert result.decision is GeometryModelDecision.FINAL_VALIDATION_CONTRADICTED
    assert result.selected_model_kind is CenterModelKind.STATIC
    assert np.array_equal(result.selected_membership, result.static_membership)


def test_rank_deficiency_and_framework_only_predictor_gate_are_fail_closed():
    x = np.linspace(-1.0, 1.0, 60)
    predictors = np.column_stack((x, x))
    local = np.column_stack((0.2 * x, np.zeros(60), np.zeros(60)))
    fingerprint, table, region, plan, _ = _inputs(local, predictors)
    result = analyze_geometry_conditioned_state_samples(
        fingerprint=fingerprint,
        predictor_table=table,
        frozen_region=region,
        block_plan=plan,
    )
    assert result.decision is GeometryModelDecision.RANK_DEFICIENT
    assert result.dynamic_model is None
    with pytest.raises(GeometryConditioningInputError):
        FrameworkPredictorTable(
            0, 0, "ring:state-0", np.arange(3), np.arange(3), np.zeros(3, dtype=int),
            ("ion_x",), np.zeros((3, 1)), VIEW, framework_only=False,
        )


def test_moving_boundary_crossing_is_not_silently_called_ion_driven():
    frames = np.tile(np.arange(60), 2)
    ions = np.repeat([0, 1], 60)
    x_frame = np.linspace(-1.0, 1.0, 60)
    predictors = np.tile(x_frame, 2)[:, None]
    moving_center = 0.22 + 0.22 * x_frame
    local = np.zeros((120, 3))
    local[:60, 0] = moving_center
    local[60:, 0] = 0.22  # second ion is nearly fixed while the boundary sweeps.
    fingerprint, table, region, _plan, _ = _inputs(
        local, predictors, frames=frames, ions=ions, core=0.08, basin=0.28,
    )
    plan = EvidenceBlockPlan(tuple(range(0, 20)), tuple(range(20, 40)), tuple(range(40, 60)))
    result = analyze_geometry_conditioned_state_samples(
        fingerprint=fingerprint,
        predictor_table=table,
        frozen_region=region,
        block_plan=plan,
        options=GeometryConditioningOptions(boundary_induced_ratio=0.6),
    )
    assert result.dynamic_model is not None
    assert any(c.drive_status is CrossingDriveStatus.BOUNDARY_INDUCED for c in result.crossings)
    crossing = next(c for c in result.crossings if c.drive_status is CrossingDriveStatus.BOUNDARY_INDUCED)
    assert crossing.boundary_induced_crossing is True
    assert crossing.ion_displacement_norm < crossing.center_displacement_norm


def test_static_and_dynamic_memberships_are_both_persistent_and_nested():
    x = np.linspace(-1.0, 1.0, 60)[:, None]
    local = np.column_stack((0.3 * x[:, 0], np.zeros(60), np.zeros(60)))
    fingerprint, table, region, plan, _ = _inputs(local, x, core=0.08, basin=0.20)
    result = analyze_geometry_conditioned_state_samples(
        fingerprint=fingerprint, predictor_table=table, frozen_region=region, block_plan=plan
    )
    assert np.all(result.static_membership <= int(RegionMembership.CORE))
    assert np.all(result.dynamic_membership <= int(RegionMembership.CORE))
    assert not np.array_equal(result.static_membership, result.dynamic_membership)
    assert np.array_equal(result.selected_membership, result.dynamic_membership)


def test_catalog_overlap_conflicts_and_occupancy_bounds_are_exclusive():
    rng = np.random.default_rng(32)
    x = np.linspace(-1.0, 1.0, 60)[:, None]
    local0 = rng.normal(scale=0.02, size=(60, 3))
    local1 = rng.normal(scale=0.02, size=(60, 3))
    fp0, table0, region0, plan, _ = _inputs(local0, x, state=0, identity="ring:first", core=0.10, basin=0.25)
    fp1, table1, region1, _plan, _ = _inputs(local1, x, state=1, identity="ring:second", core=0.10, basin=0.25)
    fingerprints = CoordinationFingerprintCatalog(
        "a" * 64, "b" * 64, "c" * 64, VALIDATED, VIEW, "f" * 64,
        CoordinationFingerprintOptions(), CoordinationFingerprintResourcePolicy(), (fp0, fp1),
    )
    validated = SimpleNamespace(signature=VALIDATED, block_plan=plan)
    catalog = prepare_geometry_conditioned_site_catalog(
        validated, fingerprints, (table0, table1), (region0, region1)
    )
    assert any(v.status is AssignmentConflictStatus.MULTIPLE_CORE_OVERLAP for v in catalog.assignment_conflicts)
    assert all(v.lower_fraction <= v.upper_fraction for v in catalog.occupancy_bounds)
    assert all(v.core_overlap_fraction > 0.0 for v in catalog.occupancy_bounds)
    assert len(catalog.assignment_conflicts) == 60
    replay = GeometryConditionedSiteCatalog.from_dict(catalog.to_dict())
    assert replay.signature == catalog.signature
    payload = copy.deepcopy(catalog.to_dict())
    payload["assignment_conflicts"][0]["status"] = AssignmentConflictStatus.UNIQUE_CORE.value
    with pytest.raises(GeometryConditioningInputError):
        GeometryConditionedSiteCatalog.from_dict(payload)


def test_serialization_tamper_source_binding_resources_and_public_api():
    x = np.linspace(-1.0, 1.0, 60)[:, None]
    local = np.column_stack((0.25 * x[:, 0], np.zeros(60), np.zeros(60)))
    fingerprint, table, region, plan, _ = _inputs(local, x)
    refinement = analyze_geometry_conditioned_state_samples(
        fingerprint=fingerprint, predictor_table=table, frozen_region=region, block_plan=plan
    )
    # Verify the source-bound state record independently; the complete catalog is exercised above.
    replay = type(refinement).from_dict(refinement.to_dict())
    assert replay.signature == refinement.signature
    payload = copy.deepcopy(refinement.to_dict())
    payload["candidate_dynamic_centers"][0][0] += 0.5
    with pytest.raises(GeometryConditioningInputError):
        type(refinement).from_dict(payload)
    with pytest.raises(GeometryConditioningResourceError):
        fingerprints = CoordinationFingerprintCatalog(
            "a" * 64, "b" * 64, "c" * 64, VALIDATED, VIEW, "f" * 64,
            CoordinationFingerprintOptions(), CoordinationFingerprintResourcePolicy(), (fingerprint,),
        )
        prepare_geometry_conditioned_site_catalog(
            SimpleNamespace(signature=VALIDATED, block_plan=plan), fingerprints, (table,), (region,),
            resources=GeometryConditioningResourcePolicy(max_states=1, max_samples=1),
        )
    with pytest.raises(GeometryConditioningInputError):
        FrozenRegionDefinition(0, 0, "ring:state-0", (0, 0, 0), 0.3, 0.2, VALIDATED)
    bad_table = replace(table, registered_structural_view_digest="9" * 64, signature="")
    fingerprints = CoordinationFingerprintCatalog(
        "a" * 64, "b" * 64, "c" * 64, VALIDATED, VIEW, "f" * 64,
        CoordinationFingerprintOptions(), CoordinationFingerprintResourcePolicy(), (fingerprint,),
    )
    with pytest.raises(GeometryConditioningInputError, match="structural view"):
        prepare_geometry_conditioned_site_catalog(
            SimpleNamespace(signature=VALIDATED, block_plan=plan), fingerprints, (bad_table,), (region,),
        )
    assert mdstats.GEOMETRY_CONDITIONING_STAGE == "11E5b"
    assert mdstats.prepare_geometry_conditioned_site_catalog is prepare_geometry_conditioned_site_catalog
