from __future__ import annotations

from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data import campaign_cli as cli
from tests.test_mlff_target_data2d_convergence import (
    _coarse,
    _ev,
    _ladder,
    _short,
)
from tests.test_mlff_data8_mace_artifacts import (
    _data7_bundles,
    _foundation,
    _probe,
)


def _selected_authority():
    ladder = _ladder()
    plan = mdstats.build_target_size_convergence_plan(ladder)
    plan = _coarse(plan, {2: 10, 4: 9, 8: 8, 16: 7, 32: 30})
    plan = _short(plan, {2: 8, 4: 7, 8: 6, 16: 5})
    short = {item.target_size: item for item in plan.short_training_evidence}
    smaller, larger = sorted(plan.stage_b_finalist_sizes)
    plan = mdstats.with_stage_c_evidence(
        plan,
        (
            _ev(
                smaller,
                8.9,
                stage="final",
                parent=short[smaller],
                replay_ok=True,
                physical_ok=True,
            ),
            _ev(
                larger,
                8.1,
                stage="final",
                parent=short[larger],
                replay_ok=True,
                physical_ok=True,
            ),
        ),
        largest_materialized_size=32,
    )
    assert plan.outcome == "selected"
    return ladder, plan


def test_active_size_study_candidates_drive_one_data7_data8_ladder():
    ladder = _ladder()
    convergence = mdstats.build_target_size_convergence_plan(ladder)

    sizes = cli._authoritative_materialization_selection_sizes(
        convergence, ladder=ladder
    )

    assert sizes == convergence.stage_a_survivor_sizes
    assert mdstats.SelectionBudgetPolicy(target_sizes=sizes).target_sizes == sizes
    variants = cli._variant_specs(
        {
            "training": {
                "modes": ["naive_fine_tuning"],
                "seeds": [1],
            },
            "selection": {"sizes": [8]},
        },
        selection_sizes=sizes,
    )
    assert tuple(item.selection_size for item in variants) == sizes


def test_selected_target_size_replaces_intermediate_candidates():
    ladder, convergence = _selected_authority()

    sizes = cli._authoritative_materialization_selection_sizes(
        convergence, ladder=ladder
    )

    assert sizes == (convergence.selected_target_size,)
    assert set(sizes).isdisjoint(
        set(convergence.stage_a_survivor_sizes) - set(sizes)
    )


def test_selected_rung_reaches_real_data8_consumer(tmp_path):
    sources, frames, frame_data, _data4, data5, _data6, bundles = (
        _data7_bundles(tmp_path)
    )

    result = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=tmp_path / "selected-data8",
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(
            device="cpu", max_num_epochs=2
        ),
        selection_size=4,
        require_foundation_residual_e0=False,
    )

    assert {job.protocol.selection_size for job in result.jobs} == {4}


def test_selected_target_size_must_exist_in_authoritative_ladder():
    _ladder_authority, convergence = _selected_authority()
    missing_selected = SimpleNamespace(
        materialized_target_sizes=tuple(
            size
            for size in convergence.stage_a_survivor_sizes
            if size != convergence.selected_target_size
        )
    )

    with pytest.raises(
        cli.CampaignCliError,
        match="selected target size.*absent from the authoritative TARGET-DATA2C",
    ):
        cli._authoritative_materialization_selection_sizes(
            convergence, ladder=missing_selected
        )


def test_terminal_failure_cannot_fall_back_to_intermediate_candidates():
    ladder, convergence = _selected_authority()
    payload = convergence.to_dict()
    payload.pop("content_digest")
    payload["selected_target_size"] = None
    payload["outcome"] = "failed"
    failed = mdstats.TargetSizeConvergencePlan.from_dict(payload)

    with pytest.raises(
        cli.CampaignCliError,
        match="cannot authorize DATA8 materialization without a selected target size",
    ):
        cli._authoritative_materialization_selection_sizes(
            failed, ladder=ladder
        )
