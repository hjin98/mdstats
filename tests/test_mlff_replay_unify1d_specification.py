from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_replay_unify1d_release_architecture_and_generated_interface_are_synchronized():
    assert tuple(int(v) for v in mdstats.__version__.split("a",1)[0].split(".")) >= (0, 20, 213)
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV80.md").read_text(encoding="utf-8")
    assert "Revision 80 current gate: REPLAY-UNIFY1D" in manual
    assert "REPLAY-UNIFY1D implementation boundary" in manual
    assert "mdstats.replay-source-artifact-receipt.v1" in manual
    assert "10,000 train plus 2,000 monitor" in manual
    assert "0.20.213a0" in note
    assert "Dependency-graph schema:** 62" in note

    config = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_set="replay_fps_12000.extxyz",
    )
    parsed = tomllib.loads(config)
    assert parsed["paths"]["replay_set"] == "replay_fps_12000.extxyz"
    assert "replay_train" not in parsed["paths"]
    assert "replay_monitor" not in parsed["paths"]
    assert "replay_true_labels" not in parsed["paths"]


def test_dependency_graph_records_gate_d_as_live_campaign_integration():
    graph_path = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 80
    assert graph["schema_version"] >= 62
    assert graph["documentation_gate"] in {"REPLAY_UNIFY1D_CAMPAIGN_INTEGRATION", "REPLAY_UNIFY1E_MIGRATION_HARDENING", "CUEQ_DEFAULT1_HF2_TRAIN2_FP32_PARITY_CEILING", "CUEQ_TRAIN2_REPEATABILITY_DIAGNOSTIC_HF", "CUEQ_TRAIN2_REPEATABILITY_DIAGNOSTIC_REFINEMENT", "CUEQ_TRAIN2_REPEATABILITY_DIAGNOSTIC_ALLPAIRS", "CUEQ_TRAIN2_NOISE_NORMALIZED_PARITY"}
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["REPLAY_UNIFY1D_CAMPAIGN_INTEGRATION"]
    assert gate["implementation_status"] == "implemented_campaign_integration"
    assert gate["implemented_release"] == "0.20.213a0"
    assert gate["production_replay_execution_changed"] is True
    assert gate["new_generated_config_path"] == "replay_set"
    assert gate["mixed_interface_forbidden"] is True
    assert gate["legacy_split_schema_readable"] is True
    assert gate["legacy_init_flags_hidden"] is True
    assert gate["doctor_full_pseudolabel_inference_deferred_to_prepare"] is True
    assert gate["source_receipt_schema"] == "mdstats.replay-source-artifact-receipt.v1"
    assert gate["supplied_lta_default_split_counts"] == [10000, 2000]
    assert gate["real_mace_gpu_execution_status"] in {"deferred", "deferred_to_regenerated_final_gpu1_workstation_run"}
    assert gate["next_gate"] in {"REPLAY_UNIFY1E_MIGRATION_HARDENING", "REPLAY_UNIFY1E_MIGRATION_HARDENING_COMPLETE"}
    assert nodes["REPLAY_UNIFY1E_MIGRATION_HARDENING"]["implementation_status"] in {"planned_frozen", "implemented_migration_hardening_final_gpu1_regenerated"}
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").is_file()


def test_gate_d_public_cli_hides_legacy_init_replay_flags_but_parser_remains_compatible():
    parser = campaign_cli.build_parser()
    subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    init_parser = subparsers.choices["init"]
    help_text = init_parser.format_help()
    assert "--replay-set" in help_text
    assert "--replay-train" not in help_text
    assert "--replay-monitor" not in help_text
    assert "--replay-true-labels" not in help_text

    historical = parser.parse_args([
        "init", "--replay-train", "train.extxyz", "--replay-monitor", "monitor.extxyz"
    ])
    assert historical.replay_train == "train.extxyz"
    assert historical.replay_monitor == "monitor.extxyz"


def test_gate_d_qualification_evidence_is_cpu_integration_and_gpu_deferred():
    payload = json.loads((ROOT / "benchmarks/mlff_replay_unify1d_cpu_integration_2026-08-16.json").read_text(encoding="utf-8"))
    assert payload["release"] == "0.20.213a0"
    assert payload["source"]["configuration_count"] == 12000
    assert payload["counts"] == {"train": 10000, "monitor": 2000}
    assert payload["qualification_scope"] == "single_source_campaign_integration_true_dft_plus_deterministic_pseudolabel_tests"
    assert payload["gpu_mace_execution_status"].startswith("deferred")
    assert payload["timings_seconds"]["process_style_restart"] < 2.0
