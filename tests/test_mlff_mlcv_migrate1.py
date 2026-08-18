from types import SimpleNamespace
from pathlib import Path

import pytest
import mdstats

from mdstats.training_data.campaign_cli import (
    CampaignCliError,
    _enforce_evaluation_migration_boundary,
)


def _catalog(d):
    return SimpleNamespace(content_digest=d)


def _bundle(role='1'*64, monitor='2'*64):
    return SimpleNamespace(
        mlcv_role_catalog=_catalog(role),
        mlcv_monitor_catalog=_catalog(monitor),
    )


def test_migrate1_lifecycle_is_distinct_from_historical_adaptive_topk():
    campaign = SimpleNamespace(content_digest='a'*64)
    authority = mdstats.build_mlcv_lifecycle_authority(
        campaign, (_bundle(),), source_checkpoint_strategy='mlcv_nested_cv'
    )
    assert authority is not None
    assert authority.checkpoint_strategy == 'mlcv_nested_cv'
    assert authority.source_checkpoint_strategy == 'mlcv_nested_cv'
    assert authority.candidate_limit_per_run == 5
    assert authority.permits_config_strategy('mlcv_nested_cv')
    assert not authority.permits_config_strategy('adaptive_topk')
    restored = mdstats.MlcvLifecycleAuthorityRecord.from_dict(authority.to_dict())
    assert restored.content_digest == authority.content_digest


def test_migrate1_transitional_020131_020138_alias_can_reopen_without_reinterpretation():
    campaign = SimpleNamespace(content_digest='a'*64)
    authority = mdstats.build_mlcv_lifecycle_authority(
        campaign, (_bundle(),), source_checkpoint_strategy='adaptive_topk'
    )
    assert authority is not None
    assert authority.checkpoint_strategy == 'mlcv_nested_cv'
    assert authority.source_checkpoint_strategy == 'adaptive_topk'
    assert authority.permits_config_strategy('adaptive_topk')
    assert authority.permits_config_strategy('mlcv_nested_cv')
    _enforce_evaluation_migration_boundary(campaign, 'adaptive_topk', authority)
    _enforce_evaluation_migration_boundary(campaign, 'mlcv_nested_cv', authority)
    with pytest.raises(CampaignCliError, match='frozen to conventional MLCV'):
        _enforce_evaluation_migration_boundary(campaign, 'bounded', authority)


def test_migrate1_catalog_authority_allows_shared_role_catalog_across_monitor_variants():
    campaign = SimpleNamespace(content_digest='a'*64)
    authority = mdstats.build_mlcv_lifecycle_authority(
        campaign,
        (_bundle('1'*64, '2'*64), _bundle('1'*64, '3'*64)),
    )
    assert authority is not None
    assert authority.role_catalog_digests == ('1'*64,)
    assert authority.monitor_catalog_digests == ('2'*64, '3'*64)


def test_migrate1_rejects_mixed_pre_mlcv_and_mlcv_data8_authority():
    campaign = SimpleNamespace(content_digest='a'*64)
    old = SimpleNamespace(mlcv_role_catalog=None, mlcv_monitor_catalog=None)
    with pytest.raises(mdstats.TrainingDataInputError, match='mixes MLCV and pre-MLCV'):
        mdstats.build_mlcv_lifecycle_authority(campaign, (_bundle(), old))


def test_migrate1_protocol_freeze_roundtrip_and_generic_storage_authority():
    freeze = mdstats.MlcvProtocolFreezeRecord(
        production_qualification_digest='1'*64,
        campaign_plan_digest='2'*64,
        lifecycle_authority_digest='3'*64,
        lightweight_ranking_record_digests=('4'*64, '5'*64),
        run_selection_record_digests=('6'*64, '7'*64),
        campaign_cv_aggregate_digest='8'*64,
        final_selection_record_digest='9'*64,
        final_committee_record_digest='a'*64,
        verification_record_digest='b'*64,
        locked_test_record_digest='c'*64,
        production_model_record_digest='d'*64,
        protected_checkpoint_sha256=('e'*64, 'f'*64),
        protected_model_sha256=('0'*64, '1'*64),
        model_inference_dtype='float32',
        scientific_analysis_dtype='float64',
        frozen_at_utc='2026-08-10T12:00:00Z',
    )
    restored = mdstats.MlcvProtocolFreezeRecord.from_dict(freeze.to_dict())
    assert restored.content_digest == freeze.content_digest
    generic = mdstats.protocol_freeze_authority_from_mlcv(freeze)
    assert generic.authority_kind == 'mlcv_deployment'
    assert generic.source_record_digest == freeze.content_digest
    assert set(generic.protected_model_sha256) == set(freeze.protected_model_sha256)
    parsed = mdstats.protocol_freeze_authority_from_payload(freeze.to_dict())
    assert parsed.content_digest == generic.content_digest


def test_migrate1_receipt_is_immutable_and_preserves_historical_keys():
    record = mdstats.MlcvMigrationRecord(
        campaign_plan_digest='1'*64,
        lifecycle_authority_digest='2'*64,
        mlcv_protocol_freeze_digest='3'*64,
        protocol_freeze_authority_digest='4'*64,
        historical_evidence_keys=('committee', 'adaptive_full_evaluation', 'committee'),
        migrated_at_utc='2026-08-10T12:00:00Z',
    )
    assert record.historical_evidence_keys == ('adaptive_full_evaluation', 'committee')
    restored = mdstats.MlcvMigrationRecord.from_dict(record.to_dict())
    assert restored.content_digest == record.content_digest


def test_migrate1_generated_default_uses_distinct_mlcv_strategy_and_storage_guard():
    source = Path('mdstats/training_data/campaign_cli.py').read_text(encoding='utf-8')
    example = Path('campaign.toml.example').read_text(encoding='utf-8')
    assert 'checkpoint_strategy = "mlcv_nested_cv"' in source
    assert 'checkpoint_strategy = "mlcv_nested_cv"' in example
    assert 'STOR2 retained MLCV checkpoints' in source
    assert 'mlcv_protocol_freeze' in source
    assert 'mlcv_migration' in source
