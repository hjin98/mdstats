from __future__ import annotations

from types import SimpleNamespace

import mdstats
import pytest

from mdstats.training_data import campaign_cli
from mdstats.training_data import _campaign_cli_core as campaign_core


def _bundle(role: str = "1" * 64, monitor: str = "2" * 64) -> SimpleNamespace:
    return SimpleNamespace(
        mlcv_role_catalog=SimpleNamespace(content_digest=role),
        mlcv_monitor_catalog=SimpleNamespace(content_digest=monitor),
    )


def _campaign(digest: str = "9" * 64) -> SimpleNamespace:
    return SimpleNamespace(content_digest=digest)


def _store(tmp_path):
    return campaign_cli.CampaignStore(tmp_path / "campaign.sqlite3")


@pytest.mark.parametrize("runtime_strategy", ("bounded", "train2_target_first"))
def test_non_mlcv_target_size_runtime_does_not_admit_lifecycle_from_bundle_provenance(
    runtime_strategy, tmp_path
):
    store = _store(tmp_path)
    try:
        result = campaign_cli._reconcile_mlcv_lifecycle_authority(
            _campaign(),
            (_bundle(),),
            store,
            requested_checkpoint_strategy=runtime_strategy,
        )
        assert result is None
        assert not store.has_record("mlcv_lifecycle_authority")
    finally:
        store.close()


def test_canonical_mlcv_runtime_admits_canonical_lifecycle_and_is_idempotent(tmp_path):
    store = _store(tmp_path)
    try:
        first = campaign_cli._reconcile_mlcv_lifecycle_authority(
            _campaign(), (_bundle(),), store,
            requested_checkpoint_strategy=mdstats.MLCV_CHECKPOINT_STRATEGY,
        )
        second = campaign_cli._reconcile_mlcv_lifecycle_authority(
            _campaign(), (_bundle(),), store,
            requested_checkpoint_strategy=mdstats.MLCV_CHECKPOINT_STRATEGY,
        )
        assert first is not None
        assert second is not None
        assert first.source_checkpoint_strategy == mdstats.MLCV_CHECKPOINT_STRATEGY
        assert first.checkpoint_strategy == mdstats.MLCV_CHECKPOINT_STRATEGY
        assert second.content_digest == first.content_digest
    finally:
        store.close()


def test_transitional_adaptive_alias_is_explicitly_recorded_as_legacy_source(tmp_path):
    store = _store(tmp_path)
    try:
        authority = campaign_cli._reconcile_mlcv_lifecycle_authority(
            _campaign(), (_bundle(),), store,
            requested_checkpoint_strategy=mdstats.MLCV_TRANSITIONAL_STRATEGY_ALIAS,
        )
        assert authority is not None
        assert authority.source_checkpoint_strategy == mdstats.MLCV_TRANSITIONAL_STRATEGY_ALIAS
        assert authority.checkpoint_strategy == mdstats.MLCV_CHECKPOINT_STRATEGY
    finally:
        store.close()


def test_existing_lifecycle_source_wins_over_current_runtime_policy(tmp_path):
    store = _store(tmp_path)
    try:
        historical = mdstats.MlcvLifecycleAuthorityRecord(
            campaign_plan_digest=_campaign().content_digest,
            role_catalog_digests=("1" * 64,),
            monitor_catalog_digests=("2" * 64,),
            source_checkpoint_strategy=mdstats.MLCV_TRANSITIONAL_STRATEGY_ALIAS,
        )
        store.put_record("mlcv_lifecycle_authority", historical)
        current = campaign_cli._reconcile_mlcv_lifecycle_authority(
            _campaign(), (_bundle(),), store,
            requested_checkpoint_strategy="train2_target_first",
        )
        assert current is not None
        assert current.source_checkpoint_strategy == mdstats.MLCV_TRANSITIONAL_STRATEGY_ALIAS
        assert current.content_digest == historical.content_digest
    finally:
        store.close()


@pytest.mark.parametrize(
    ("source", "checkpoint"),
    [
        ("bounded", mdstats.MLCV_CHECKPOINT_STRATEGY),
        (mdstats.MLCV_CHECKPOINT_STRATEGY, "adaptive_topk"),
    ],
)
def test_lifecycle_record_keeps_strict_source_and_requested_validation(source, checkpoint):
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.MlcvLifecycleAuthorityRecord(
            campaign_plan_digest="9" * 64,
            role_catalog_digests=("1" * 64,),
            monitor_catalog_digests=("2" * 64,),
            source_checkpoint_strategy=source,
            checkpoint_strategy=checkpoint,
        )


def test_target_size_funnel_reaches_epoch_boundaries_without_synthesizing_mlcv_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    active = (
        SimpleNamespace(
            outcome=mdstats.OUTCOME_AWAITING_COARSE_SCREEN,
            next_training_epoch=3,
            next_training_sizes=(512, 1024, 2048, 4096, 8192),
            selected_target_size=None,
            decision_reason="fixture",
            content_digest="3" * 64,
            candidate_authority_digest="4" * 64,
            policy=SimpleNamespace(screening_optimizer_seeds=(1, 2)),
        ),
        SimpleNamespace(
            outcome=mdstats.OUTCOME_AWAITING_SHORT_SCREEN,
            next_training_epoch=10,
            next_training_sizes=(1024, 2048),
            selected_target_size=None,
            decision_reason="fixture",
            content_digest="5" * 64,
            candidate_authority_digest="6" * 64,
            policy=SimpleNamespace(screening_optimizer_seeds=(1, 2)),
        ),
        SimpleNamespace(
            outcome=mdstats.OUTCOME_AWAITING_FINAL_SCREEN,
            next_training_epoch=30,
            next_training_sizes=(2048,),
            selected_target_size=None,
            decision_reason="fixture",
            content_digest="7" * 64,
            candidate_authority_digest="8" * 64,
            policy=SimpleNamespace(screening_optimizer_seeds=(1, 2)),
        ),
        SimpleNamespace(
            outcome=mdstats.OUTCOME_SELECTED,
            next_training_epoch=None,
            next_training_sizes=(),
            selected_target_size=2048,
            decision_reason="fixture",
            content_digest="9" * 64,
            candidate_authority_digest="a" * 64,
            policy=SimpleNamespace(screening_optimizer_seeds=(1, 2)),
        ),
    )
    holder = {"index": 0}
    epochs: list[int] = []
    cfg = {"training": {"policy_generation": "train2"}}
    paths = SimpleNamespace(state_db=tmp_path / "campaign.sqlite3")
    store = campaign_cli.CampaignStore(paths.state_db)
    monkeypatch.setattr(campaign_core, "_load_config", lambda _path: (cfg, paths))
    monkeypatch.setattr(campaign_core, "CampaignStore", lambda _path: store)
    monkeypatch.setattr(
        campaign_core,
        "_load_verified_target_size_study_authority",
        lambda _store: active[holder["index"]],
    )
    monkeypatch.setattr(
        campaign_core,
        "_require_train2_preflight_authorization",
        lambda *_args: None,
    )

    def fake_train(_args):
        study = active[holder["index"]]
        epochs.append(study.next_training_epoch)
        authority = campaign_core._reconcile_mlcv_lifecycle_authority(
            _campaign(), (_bundle(),), store,
            requested_checkpoint_strategy="train2_target_first",
        )
        assert authority is None
        assert not store.has_record("mlcv_lifecycle_authority")
        return 0

    def fake_evaluate(_args):
        holder["index"] += 1
        return 0

    monkeypatch.setattr(campaign_core, "_execute_train_current_authority", fake_train)
    monkeypatch.setattr(campaign_core, "_execute_evaluate_current_authority", fake_evaluate)
    try:
        assert campaign_core.command_select_target_size(
            SimpleNamespace(config="campaign.toml")
        ) == 0
    finally:
        store.close()
    assert epochs == [3, 10, 30]
