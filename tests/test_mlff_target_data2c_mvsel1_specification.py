from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mvsel1_release_manual_and_spec_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 69" in manual
    assert "TARGET-DATA2C-MVSEL1 - implemented deterministic progressive multi-view selector" in manual
    assert "w_w / (1 + n_w)" in manual
    assert "revision-64 TARGET-DATA2C v4 remains the production selector" in manual
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2c_mvsel1_progressive_selector_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.202a0`" in spec
    assert "weight / (1 + selected_multiplicity)" in spec
    assert "TARGET-DATA2C-REPAIR1" in spec


def test_mvsel1_dependency_graph_marks_gate_implemented_and_next_gate_planned():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    assert graph["documentation_gate"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION"
    nodes = {node["id"]: node for node in graph["nodes"]}
    selector = nodes["TARGET_DATA2C_MVSEL1_PROGRESSIVE_SELECTOR"]
    assert selector["implementation_status"] == "implemented_diagnostic_pre_migration"
    assert selector["implemented_release"] == "0.20.202a0"
    assert selector["record_name"] == "target_multi_view_selection"
    assert selector["runtime_selector_changed"] is False
    assert selector["representative_gain"] == "harmonic_witness_multiplicity"
    assert selector["gain_accumulation"] == "FP64"
    assert selector["next_gate"] == "TARGET_DATA2C_REPAIR1_DEFICIT_EXCHANGE"
    assert nodes["TARGET_DATA2C_REPAIR1_DEFICIT_EXCHANGE"]["implementation_status"] == "implemented_diagnostic_pre_migration"


def test_mvsel1_campaign_integration_is_pre_migration():
    cli = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert '"target_multi_view_selection"' in cli
    assert "_ensure_target_multi_view_selection" in cli
    assert "build_target_multi_view_selection_plan" in cli
    assert "TARGET-DATA2C v4 unchanged" in cli
    module = (ROOT / "mdstats/training_data/target_multi_view_selector.py").read_text()
    assert "harmonic_witness_multiplicity" in module
    assert "stable frame UID" in module
    assert "incremental" in module.lower()


def test_mvsel1_changelog_and_patch_notes_are_current():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.202a0.md").read_text()
    assert "TARGET-DATA2C-MVSEL1" in patch
    assert "pre-migration" in patch
