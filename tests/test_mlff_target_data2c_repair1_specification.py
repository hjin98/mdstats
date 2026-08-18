from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_repair1_release_manual_and_spec_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 70" in manual
    assert "TARGET-DATA2C-REPAIR1 - implemented exact active-shell deficit-directed repair" in manual
    assert "selected required-obligation multiplicities" in manual
    assert "revision-64 TARGET-DATA2C v4 remains the production selector" in manual
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2c_repair1_deficit_exchange_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.203a0`" in spec
    assert "literal K-times leave-one-out" in spec
    assert "replacement inherits the removed rank" in spec
    assert "TARGET-DATA2C-MVPERF1" in spec


def test_repair1_dependency_graph_marks_gate_implemented_and_mvperf_next():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    assert graph["documentation_gate"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION"
    nodes = {node["id"]: node for node in graph["nodes"]}
    repair = nodes["TARGET_DATA2C_REPAIR1_DEFICIT_EXCHANGE"]
    assert repair["implementation_status"] == "implemented_diagnostic_pre_migration"
    assert repair["implemented_release"] == "0.20.203a0"
    assert repair["record_name"] == "target_multi_view_repair"
    assert repair["runtime_selector_changed"] is False
    assert repair["exact_required_obligation_multiplicity"] is True
    assert repair["strict_no_coverage_regression"] is True
    assert repair["replacement_rank_inheritance"] is True
    assert repair["active_shell_only"] is True
    assert repair["next_gate"] == "TARGET_DATA2C_MVPERF1_EXACT_HARDENING"
    assert nodes["TARGET_DATA2C_MVPERF1_EXACT_HARDENING"]["implementation_status"] == "implemented_exact_performance_hardening"


def test_repair1_campaign_integration_remains_pre_migration():
    cli = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert '"target_multi_view_repair"' in cli
    assert "_ensure_target_multi_view_repair" in cli
    assert "build_target_multi_view_repair_plan" in cli
    assert "TARGET-DATA2C v4 unchanged" in cli
    assert "target_multi_view_repair" in __import__("mdstats.training_data.campaign_cli", fromlist=["_PREPARE_RECEIPT_RECORD_KEYS"])._PREPARE_RECEIPT_RECORD_KEYS


def test_repair1_module_freezes_exact_multiplicity_and_rank_contracts():
    module = (ROOT / "mdstats/training_data/target_multi_view_repair.py").read_text()
    selector = (ROOT / "mdstats/training_data/target_multi_view_selector.py").read_text()
    assert "multiplicity == 1" in module or "multiplicity[witnesses] == 1" in module
    assert "replacement_rank_inheritance" in module
    assert "active_shell_only" in module
    assert "strict_no_coverage_regression" in module
    assert "Keep the exact selected multiplicity" in selector


def test_repair1_changelog_and_patch_notes_are_current():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.203a0.md").read_text()
    assert "TARGET-DATA2C-REPAIR1" in patch
    assert "active shell" in patch
