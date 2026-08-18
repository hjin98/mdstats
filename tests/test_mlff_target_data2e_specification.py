from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats
from mdstats.training_data import campaign_cli as cli


def test_target_data2e_public_surface_is_exported():
    for name in (
        "TARGET_PRODUCTION_CORPUS_VERSION",
        "TargetProductionCorpusDecisionError",
        "TargetProductionRungProvenance",
        "TargetProductionEquivalenceComparison",
        "TargetProductionDomainDecision",
        "TargetProductionCorpusDecision",
        "build_target_production_corpus_decision",
        "validate_target_production_corpus_decision",
    ):
        assert hasattr(mdstats, name), name


def test_target_data2e_does_not_invalidate_prepare_contract():
    contract = cli._prepare_contract_signature()
    assert "target_data2e_production_corpus_version" not in contract
    assert "target_data2d_convergence_version" not in contract


def test_campaign_target_data2e_helpers_are_available_but_not_provisional():
    assert callable(cli._load_verified_target_production_corpus_decision)
    assert callable(cli._ensure_target_production_corpus_decision)
    # TARGET-DATA2E is downstream of Stage C and therefore cannot be part of a
    # prepare receipt that is legitimately written while Stage B/C are pending.
    assert "target_production_corpus_decision" not in cli._PREPARE_RECEIPT_RECORD_KEYS


def test_campaign_store_materializes_and_reuses_target_data2e_only_after_selection(tmp_path):
    from tests.test_mlff_target_data2e_production_corpus import _build_authorities

    role, audit, reference, ladder, selected = _build_authorities()
    store = cli.CampaignStore(tmp_path / "state.sqlite3")
    store.put_record("target_data_role_freeze", role)
    store.put_record("foundation_target_audit", audit)
    store.put_record("target_coverage_reference", reference)
    store.put_record("target_data_ladder", ladder)

    waiting = mdstats.build_target_size_convergence_plan(ladder)
    store.put_record("target_size_convergence", waiting)
    assert cli._ensure_target_production_corpus_decision(store) is None
    assert not store.has_record("target_production_corpus_decision")

    store.put_record("target_size_convergence", selected)
    first = cli._ensure_target_production_corpus_decision(store)
    second = cli._ensure_target_production_corpus_decision(store)
    assert first is not None and second is not None
    assert first.content_digest == second.content_digest
    restored = cli._load_verified_target_production_corpus_decision(store)
    assert restored.content_digest == first.content_digest



def test_campaign_target_data2e_deletes_premature_record_and_blocks_failed_funnel(tmp_path):
    from tests.test_mlff_target_data2e_production_corpus import _build_authorities

    role, audit, reference, ladder, selected = _build_authorities()
    store = cli.CampaignStore(tmp_path / "state.sqlite3")
    for key, value in (
        ("target_data_role_freeze", role),
        ("foundation_target_audit", audit),
        ("target_coverage_reference", reference),
        ("target_data_ladder", ladder),
        ("target_size_convergence", selected),
    ):
        store.put_record(key, value)
    decision = cli._ensure_target_production_corpus_decision(store)
    assert decision is not None and store.has_record("target_production_corpus_decision")

    waiting = mdstats.build_target_size_convergence_plan(ladder)
    store.put_record("target_size_convergence", waiting)
    assert cli._ensure_target_production_corpus_decision(store) is None
    assert not store.has_record("target_production_corpus_decision")

    failed = replace(
        selected,
        selected_target_size=None,
        outcome="failed",
        decision_reason="synthetic Stage-C qualification failure",
    )
    store.put_record("target_size_convergence", failed)
    with pytest.raises(cli.CampaignCliError, match="completed without convergence"):
        cli._ensure_target_production_corpus_decision(store)
    assert not store.has_record("target_production_corpus_decision")

def test_target_data2e_manual_records_implementation_and_fail_closed_boundary():
    from pathlib import Path
    manual = (Path(__file__).parents[1] / "docs" / "arch_manuals" / "mlff_training_data_architecture.md").read_text(encoding="utf-8")
    assert "TARGET-DATA2E is implemented in `mdstats 0.20.168a0`" in manual
    section = manual.split("## Gate TARGET-DATA2E - production target-corpus decision and provenance", 1)[1].split("## Gate TRAIN2A", 1)[0]
    assert "cannot create a provisional winner" in section
    assert "nonconverged_at_ladder_boundary" in section
    assert "exact winning frame membership" in section
    assert "all epoch-3 evidence and survivors" in section
    assert "all epoch-10 evidence and finalists" in section
