from __future__ import annotations

from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data._common import digest


def _study(outcome: str, *, selected: int | None = None):
    policy = mdstats.TargetSizeStudyPolicy(fidelity_epochs=(3, 10, 30))
    return SimpleNamespace(
        outcome=outcome,
        policy=policy,
        content_digest=digest({"study": outcome, "selected": selected}),
        qualified_sizes=(512, 1024, 2048, 4096, 8192),
        training_horizon_epochs=30,
        coarse_survivor_sizes=(1024, 2048, 4096, 8192),
        short_finalist_sizes=(4096, 8192),
        selected_target_size=selected,
    )


def test_perf_p2r_parameter_grid_matches_frozen_v5_surface() -> None:
    grid = mdstats.PerfP2RParameterGrid()
    assert grid.coarse_epoch_candidates == (1,)
    assert grid.coarse_monitor_size_candidates == (128, 256, 512, 1024)
    assert grid.coarse_equivalence_mev_per_a_candidates == (1.0,)
    assert (grid.minimum_coverage_qualified_sizes, grid.maximum_coverage_qualified_sizes) == (3, 8)
    assert (grid.coarse_survivor_limit, grid.short_survivor_limit) == (4, 2)
    assert mdstats.PerfP2RParameterGrid.from_dict(grid.to_dict()) == grid


def test_perf_p2r_stage_plan_authorizes_only_v5_incremental_work() -> None:
    coarse_stage = mdstats.build_perf_p2r_stage_plan(_study(mdstats.OUTCOME_AWAITING_COARSE_SCREEN))
    assert coarse_stage.stage == "coarse"
    assert (coarse_stage.start_epoch, coarse_stage.target_epoch) == (0, 3)
    assert coarse_stage.candidate_sizes == (512, 1024, 2048, 4096, 8192)
    assert coarse_stage.target_only_evaluation
    assert not coarse_stage.continuation_required
    assert not coarse_stage.replay_diagnostic_authorized
    assert not coarse_stage.physical_qualification_authorized

    short_stage = mdstats.build_perf_p2r_stage_plan(_study(mdstats.OUTCOME_AWAITING_SHORT_SCREEN))
    assert short_stage.stage == "short"
    assert (short_stage.start_epoch, short_stage.target_epoch) == (3, 10)
    assert short_stage.candidate_sizes == (1024, 2048, 4096, 8192)
    assert short_stage.incremental_epochs == 7
    assert short_stage.continuation_required
    assert short_stage.target_only_evaluation
    assert not short_stage.replay_diagnostic_authorized
    assert not short_stage.physical_qualification_authorized

    final_stage = mdstats.build_perf_p2r_stage_plan(_study(mdstats.OUTCOME_AWAITING_FINAL_SCREEN))
    assert final_stage.stage == "final_screen"
    assert (final_stage.start_epoch, final_stage.target_epoch) == (10, 30)
    assert final_stage.incremental_epochs == 20
    assert final_stage.candidate_sizes == (4096, 8192)
    assert final_stage.target_only_evaluation
    assert not final_stage.replay_diagnostic_authorized
    assert not final_stage.physical_qualification_authorized
    assert mdstats.PerfP2RStagePlan.from_dict(final_stage.to_dict()) == final_stage


def test_perf_p2r_production_work_is_authorized_only_after_selection() -> None:
    stage = mdstats.build_perf_p2r_stage_plan(_study(mdstats.OUTCOME_SELECTED, selected=4096))
    assert stage.stage == "production"
    assert stage.candidate_sizes == (4096,)
    assert (stage.start_epoch, stage.target_epoch) == (0, 30)
    assert not stage.target_only_evaluation
    assert stage.replay_diagnostic_authorized
    assert stage.physical_qualification_authorized

    for outcome in (
        mdstats.OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
        mdstats.OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
    ):
        with pytest.raises(mdstats.TrainingDataInputError, match="does not authorize"):
            mdstats.build_perf_p2r_stage_plan(_study(outcome))


def test_perf_p2r_exposure_uses_exact_3_10_30_incremental_geometry() -> None:
    sizes = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    exposure = mdstats.build_perf_p2r_exposure(
        sizes, (2048, 4096, 8192, 16384), (8192, 16384),
        coarse_screen_epoch=3, short_screen_epoch=10, final_screen_epoch=30, reference_training_epoch=30,
    )
    assert exposure.coarse_structure_epochs == 3 * sum(sizes)
    assert exposure.short_increment_structure_epochs == 7 * sum((2048, 4096, 8192, 16384))
    assert exposure.final_increment_structure_epochs == 20 * sum((8192, 16384))
    assert exposure.total_structure_epochs < exposure.exhaustive_structure_epochs
    assert exposure.saved_fraction > 0.0
    assert mdstats.PerfP2RExposure.from_dict(exposure.to_dict()) == exposure


def test_perf_p2r_rejects_non_nested_survivors() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="nested"):
        mdstats.build_perf_p2r_exposure(
            (128, 256, 512), (128, 1024), (128,),
            coarse_screen_epoch=3, short_screen_epoch=10, final_screen_epoch=30, reference_training_epoch=30,
        )
