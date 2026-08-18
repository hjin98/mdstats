from __future__ import annotations

import mdstats
from mdstats.training_data import campaign_cli as cli


def test_target_data2d_public_surface_is_exported():
    names = (
        "TARGET_SIZE_CONVERGENCE_VERSION",
        "TargetDataCoverageError",
        "TargetSizeConvergencePolicy",
        "TargetSizeStageARung",
        "TargetSizeTrainingEvidence",
        "TargetSizeConvergencePlan",
        "build_target_size_convergence_plan",
        "with_stage_b0_evidence",
        "with_stage_b_evidence",
        "with_stage_c_evidence",
        "validate_target_size_convergence_authority",
    )
    for name in names:
        assert hasattr(mdstats, name), name


def test_target_data2d_generated_policy_defaults_are_frozen():
    policy = cli._target_size_convergence_policy({})
    assert policy.min_coverage_qualifiers == 3
    assert policy.coarse_training_epochs == 3
    assert policy.max_coarse_training_candidates == 4
    assert policy.coarse_target_monitor_configurations == 256
    assert policy.max_short_training_candidates == 2
    assert policy.short_training_epochs == 10
    assert policy.final_training_epochs == 30
    assert policy.practical_equivalence_mev_per_a == 1.0
    assert policy.screening_optimizer_seed == 1


def test_target_data2d_policy_overrides_are_explicit():
    cfg = {
        "target_data": {
            "size_convergence": {
                "min_coverage_qualifiers": 4,
                "coarse_training_epochs": 4,
                "max_coarse_training_candidates": 5,
                "coarse_target_monitor_configurations": 128,
                "max_short_training_candidates": 2,
                "short_training_epochs": 12,
                "final_training_epochs": 36,
                "practical_equivalence_mev_per_a": 0.75,
                "coarse_practical_equivalence_mev_per_a": 1.25,
                "screening_optimizer_seed": 17,
            }
        },
        "training": {"max_num_epochs": 36, "train2_warmup_end_fraction": 0.05},
    }
    policy = cli._target_size_convergence_policy(cfg)
    assert policy.min_coverage_qualifiers == 4
    assert policy.coarse_training_epochs == 4
    assert policy.max_coarse_training_candidates == 5
    assert policy.coarse_target_monitor_configurations == 128
    assert policy.max_short_training_candidates == 2
    assert policy.short_training_epochs == 12
    assert policy.final_training_epochs == 36
    assert policy.practical_equivalence_mev_per_a == 0.75
    assert policy.coarse_practical_equivalence_mev_per_a == 1.25
    assert policy.screening_optimizer_seed == 17


def test_target_data2d_coarse_boundary_must_be_past_warmup():
    import pytest
    with pytest.raises(cli.CampaignCliError, match="strictly past TRAIN2 LR warm-up"):
        cli._target_size_convergence_policy({
            "target_data": {"size_convergence": {"coarse_training_epochs": 3, "final_training_epochs": 30}},
            "training": {"max_num_epochs": 30, "train2_warmup_end_fraction": 0.10},
        })


def test_prepare_receipt_binds_target_data2d_authority():
    assert "target_size_convergence" in cli._PREPARE_RECEIPT_RECORD_KEYS


def test_campaign_store_persists_and_reuses_stage_a_authority(tmp_path):
    from tests.test_mlff_target_data2d_convergence import _ladder

    store = cli.CampaignStore(tmp_path / "state.sqlite3")
    ladder = _ladder()
    cfg = {
        "target_data": {
            "size_convergence": {
                "min_coverage_qualifiers": 3,
                "coarse_training_epochs": 3,
                "max_coarse_training_candidates": 4,
                "coarse_target_monitor_configurations": 256,
                "max_short_training_candidates": 2,
                "short_training_epochs": 10,
                "final_training_epochs": 30,
                "practical_equivalence_mev_per_a": 1.0,
                "screening_optimizer_seed": 1,
            }
        }
    }
    first = cli._ensure_target_size_convergence(store, cfg=cfg, ladder=ladder)
    second = cli._ensure_target_size_convergence(store, cfg=cfg, ladder=ladder)
    restored = store.get_record("target_size_convergence", mdstats.TargetSizeConvergencePlan)
    assert first.content_digest == second.content_digest == restored.content_digest
    assert restored.stage_a_survivor_sizes == (2, 4, 8, 16, 32)


def test_target_coverage_policy_is_really_configurable_from_size_convergence_table():
    policy = cli._target_coverage_policy(
        {
            "target_data": {
                "size_convergence": {
                    "coverage_threshold": 0.97,
                    "coverage_resolution_mass": 0.01,
                    "coverage_leave_one_out": True,
                    "extent_quantile_alpha": 0.02,
                    "extent_default_tolerance": "none",
                }
            }
        }
    )
    assert policy.coverage_threshold == 0.97
    assert policy.coverage_resolution_mass == 0.01
    assert policy.extent_quantile_alpha == 0.02


def test_target_coverage_default_extent_tolerance_cannot_be_silently_numeric():
    import pytest
    with pytest.raises(cli.CampaignCliError, match="extent_default_tolerance"):
        cli._target_coverage_policy(
            {"target_data": {"size_convergence": {"extent_default_tolerance": 0.1}}}
        )
