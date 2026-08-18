from __future__ import annotations

import pytest

import mdstats
from tests.test_mlff_target_data2d_convergence import _ladder, _coarse, _short


def test_perf_p2r_parameter_grid_covers_deferred_size_fidelity_surface() -> None:
    grid = mdstats.PerfP2RParameterGrid()
    assert grid.coarse_epoch_candidates == (3, 4, 5)
    assert grid.coarse_monitor_size_candidates == (128, 256, 512, 1024)
    assert grid.coarse_equivalence_mev_per_a_candidates == (1.0, 2.0, 4.0)
    assert (grid.minimum_coverage_qualified_sizes, grid.maximum_coverage_qualified_sizes) == (3, 7)
    assert mdstats.PerfP2RParameterGrid.from_dict(grid.to_dict()) == grid


def test_perf_p2r_stage_plan_authorizes_only_incremental_work() -> None:
    plan = mdstats.build_target_size_convergence_plan(_ladder())
    coarse_stage = mdstats.build_perf_p2r_stage_plan(plan)
    assert coarse_stage.stage == "coarse"
    assert coarse_stage.start_epoch == 0 and coarse_stage.target_epoch == 3
    assert coarse_stage.candidate_sizes == plan.stage_a_survivor_sizes
    assert coarse_stage.target_only_evaluation
    assert not coarse_stage.continuation_required

    plan = _coarse(plan, {2: 10, 4: 9, 8: 8, 16: 7, 32: 20})
    short_stage = mdstats.build_perf_p2r_stage_plan(plan)
    assert short_stage.stage == "short"
    assert (short_stage.start_epoch, short_stage.target_epoch) == (3, 10)
    assert short_stage.candidate_sizes == tuple(sorted(plan.stage_b_survivor_sizes))
    assert short_stage.incremental_epochs == 7
    assert short_stage.continuation_required
    assert short_stage.replay_diagnostic_authorized
    assert not short_stage.physical_qualification_authorized

    plan = _short(plan, {2: 9, 4: 8, 8: 7, 16: 6})
    final_stage = mdstats.build_perf_p2r_stage_plan(plan)
    assert final_stage.stage == "final"
    assert (final_stage.start_epoch, final_stage.target_epoch) == (10, 30)
    assert final_stage.incremental_epochs == 20
    assert final_stage.candidate_sizes == tuple(sorted(plan.stage_b_finalist_sizes))
    assert final_stage.physical_qualification_authorized
    assert mdstats.PerfP2RStagePlan.from_dict(final_stage.to_dict()) == final_stage


def test_perf_p2r_exposure_is_parameterized_over_coarse_epoch() -> None:
    sizes = (128, 256, 512, 1024, 2048, 4096, 8192)
    favorable = mdstats.build_perf_p2r_exposure(
        sizes, (128, 256, 512, 1024), (128, 256), coarse_training_epochs=3
    )
    assert favorable.coarse_structure_epochs == 3 * sum(sizes)
    assert favorable.short_increment_structure_epochs == 7 * sum((128, 256, 512, 1024))
    assert favorable.final_increment_structure_epochs == 20 * sum((128, 256))
    assert favorable.total_structure_epochs == 69888
    assert favorable.exhaustive_structure_epochs == 487680
    assert favorable.saved_fraction == pytest.approx((487680 - 69888) / 487680)

    coarse5 = mdstats.build_perf_p2r_exposure(
        sizes, (128, 256, 512, 1024), (128, 256), coarse_training_epochs=5
    )
    assert coarse5.short_increment_structure_epochs == 5 * sum((128, 256, 512, 1024))
    assert coarse5.total_structure_epochs > favorable.total_structure_epochs
    assert mdstats.PerfP2RExposure.from_dict(coarse5.to_dict()) == coarse5


def test_perf_p2r_rejects_non_nested_survivors() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="nested"):
        mdstats.build_perf_p2r_exposure(
            (128, 256, 512), (128, 1024), (128,), coarse_training_epochs=3
        )


@pytest.mark.parametrize("coarse_epoch", [3, 4, 5])
def test_perf_p2r_stage_plan_accepts_every_calibration_coarse_boundary(coarse_epoch: int) -> None:
    convergence = mdstats.build_target_size_convergence_plan(
        _ladder(),
        policy=mdstats.TargetSizeConvergencePolicy(coarse_training_epochs=coarse_epoch),
    )
    stage = mdstats.build_perf_p2r_stage_plan(convergence)
    assert stage.stage == "coarse"
    assert stage.start_epoch == 0
    assert stage.target_epoch == coarse_epoch
    assert stage.incremental_epochs == coarse_epoch
    assert stage.target_only_evaluation
    assert not stage.replay_diagnostic_authorized
    assert not stage.physical_qualification_authorized
