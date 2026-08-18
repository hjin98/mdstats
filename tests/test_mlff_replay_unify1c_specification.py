from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_replay_unify1c_release_and_architecture_are_synchronized():
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV79.md").read_text(encoding="utf-8")
    assert "REPLAY-UNIFY1C implementation boundary" in manual
    assert "REPLAY-UNIFY1C implementation boundary" in manual
    assert "mdstats.replay-foundation-audit-cache.v1" in manual
    assert "threshold-only reclassification" in manual
    assert "MaceCalculatorProvider.predict_batch()" in manual
    assert "10,000 train plus 2,000 monitor" in manual
    assert "Real MACE/CUDA/CuEq replay inference remains deliberately deferred" in note
    assert "Dependency-graph schema:** 61" in note
    assert "0.20.212a0" in note


def test_dependency_graph_records_gate_c_authority_and_keeps_gate_d_deferred():
    graph_path = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 79
    assert graph["schema_version"] >= 61
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["REPLAY_UNIFY1C_PSEUDOLABEL_MATERIALIZATION"]
    assert gate["implementation_status"] == "implemented_additive_pre_migration"
    assert gate["implemented_release"] == "0.20.212a0"
    assert gate["production_replay_execution_changed"] is False
    assert gate["prediction_cache_schema"] == "mdstats.replay-foundation-prediction-cache.v1"
    assert gate["audit_cache_schema"] == "mdstats.replay-foundation-audit-cache.v1"
    assert gate["qualification_schema"] == "mdstats.replay-pseudolabel-qualification.v1"
    assert gate["pseudolabel_view_schema"] == "mdstats.replay-pseudolabel-view.v1"
    assert gate["provider_surface"] == "MaceCalculatorProvider.predict_batch"
    assert gate["threshold_only_reclassification_without_reinference"] is True
    assert gate["inference_batch_size_in_scientific_cache_identity"] is False
    assert gate["storage_shard_size_in_scientific_cache_identity"] is False
    assert gate["supplied_lta_default_split_counts"] == [10000, 2000]
    assert gate["real_mace_gpu_execution_status"] == "deferred"
    assert gate["next_gate"] == "REPLAY_UNIFY1D_CAMPAIGN_INTEGRATION"
    assert nodes["REPLAY_UNIFY1D_CAMPAIGN_INTEGRATION"]["implementation_status"] in {"planned_frozen", "implemented_campaign_integration"}
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").is_file()


def test_gate_c_public_contract_is_additive_and_production_replay_stays_legacy():
    for name in (
        "ReplayFoundationPredictionPolicy",
        "ReplayFoundationPredictionCache",
        "ReplayPseudolabelQualificationPolicy",
        "ReplayPseudolabelQualification",
        "ReplayPseudolabelViewArtifact",
        "build_replay_foundation_prediction_cache",
        "build_replay_pseudolabel_qualification",
        "materialize_replay_pseudolabel_views",
    ):
        assert hasattr(mdstats, name), name
    assert hasattr(mdstats, "ReplayPreparationPlan")
    assert hasattr(mdstats, "build_local_replay_plan")


def test_gate_c_cpu_control_plane_evidence_is_explicitly_non_mace_and_gpu_deferred():
    payload = json.loads((ROOT / "benchmarks/mlff_replay_unify1c_cpu_control_plane_2026-08-16.json").read_text(encoding="utf-8"))
    assert payload["release"] == "0.20.212a0"
    assert payload["source"]["configuration_count"] == 12000
    assert payload["counts"] == {"eligible": 12000, "rejected": 0, "train": 10000, "monitor": 2000}
    assert payload["qualification_scope"] == "cpu_control_plane_with_deterministic_non_mace_provider"
    assert payload["gpu_mace_execution_status"].startswith("deferred")
    assert payload["timings_seconds"]["threshold_only_reclassification"] < 1.0
