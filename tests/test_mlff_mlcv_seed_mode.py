from mdstats.training_data import campaign_cli


def _cfg(seed_mode):
    return {
        "selection": {"sizes": [512]},
        "training": {
            "naive_fine_tuning": {"enabled": False},
            "multihead_replay": {
                "enabled": True,
                "seeds": [1, 2, 3],
                "cross_validation_folds": 3,
                "fold_partition_seed": 104729,
                "seed_mode": seed_mode,
            },
        },
    }


def test_default_optimizer_only_keeps_paired_cv_partition_seed():
    variants = campaign_cli._variant_specs(_cfg("optimizer_only"))
    assert [v.seed for v in variants] == [1, 2, 3]
    assert {v.fold_partition_seed for v in variants} == {104729}


def test_optimizer_and_cv_partition_changes_only_per_seed_fold_seed():
    variants = campaign_cli._variant_specs(_cfg("optimizer_and_cv_partition"))
    assert len({v.fold_partition_seed for v in variants}) == 3
    assert all(v.fold_partition_seed != 104729 for v in variants)
    assert [(v.mode, v.selection_size, v.seed, v.cross_validation_folds) for v in variants] == [
        ("multihead_replay", 512, 1, 3),
        ("multihead_replay", 512, 2, 3),
        ("multihead_replay", 512, 3, 3),
    ]


def test_invalid_seed_mode_fails_closed():
    try:
        campaign_cli._training_method_specs(_cfg("diversify_everything"))
    except campaign_cli.CampaignCliError as exc:
        assert "seed_mode" in str(exc)
    else:
        raise AssertionError("invalid seed_mode should fail")
