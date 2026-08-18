from types import SimpleNamespace

import pytest

from mdstats.training_data import campaign_cli


def _bundle(mode: str):
    return SimpleNamespace(
        replay_plan=SimpleNamespace(mode=SimpleNamespace(value=mode))
    )


def test_mixed_mode_gate_uses_replay_variant_even_when_naive_is_first():
    variants = (
        ("naive_fine_tuning", 512, 1),
        ("multihead_replay", 512, 1),
    )
    naive_record = object()
    replay_record = object()

    anchor, replay_required, variant_id = campaign_cli._select_production_gate_anchor(
        variants,
        (naive_record, replay_record),
        (_bundle("none"), _bundle("foundation_pseudolabel")),
    )

    assert anchor is replay_record
    assert replay_required is True
    assert variant_id == "multihead_replay-n512-seed1"


def test_naive_only_gate_does_not_require_replay():
    record = object()
    anchor, replay_required, variant_id = campaign_cli._select_production_gate_anchor(
        (("naive_fine_tuning", 512, 2),),
        (record,),
        (_bundle("none"),),
    )

    assert anchor is record
    assert replay_required is False
    assert variant_id == "naive_fine_tuning-n512-seed2"


def test_replay_variant_without_replay_binding_is_rejected():
    with pytest.raises(campaign_cli.CampaignCliError, match="replay corpus is not bound"):
        campaign_cli._select_production_gate_anchor(
            (("multihead_replay", 512, 2),),
            (object(),),
            (_bundle("none"),),
        )


def test_naive_variant_with_replay_binding_is_rejected():
    with pytest.raises(campaign_cli.CampaignCliError, match="unexpectedly binds"):
        campaign_cli._select_production_gate_anchor(
            (("naive_fine_tuning", 512, 2),),
            (object(),),
            (_bundle("foundation_pseudolabel"),),
        )
