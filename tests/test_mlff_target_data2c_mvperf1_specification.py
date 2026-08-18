from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mvperf1_release_manual_and_spec_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 71" in manual
    assert "TARGET-DATA2C-MVPERF1 - implemented exact-equivalence sparse execution hardening" in manual
    assert "262,144" in manual
    assert "reference" in manual and "optimized" in manual
    assert "revision-64 TARGET-DATA2C v4 remains the production selector" in manual
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2c_mvperf1_exact_hardening_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.204a0`" in spec
    assert "byte-identical" in spec
    assert "TARGET-DATA2C-MVQUAL1" in spec


def test_mvperf1_dependency_graph_marks_gate_implemented_and_next_gate():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    assert graph["documentation_gate"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION"
    nodes = {node["id"]: node for node in graph["nodes"]}
    perf = nodes["TARGET_DATA2C_MVPERF1_EXACT_HARDENING"]
    assert perf["implementation_status"] == "implemented_exact_performance_hardening"
    assert perf["implemented_release"] == "0.20.204a0"
    assert perf["maximum_scatter_edges_per_batch"] == 262144
    assert perf["reference_execution_mode_retained"] is True
    assert perf["runtime_selector_changed"] is False
    assert perf["next_gate"] == "TARGET_DATA2C_MVQUAL1_SAME_N_QUALIFICATION"


def test_mvperf1_code_freezes_exact_execution_and_resource_contracts():
    selector = (ROOT / "mdstats/training_data/target_multi_view_selector.py").read_text()
    repair = (ROOT / "mdstats/training_data/target_multi_view_repair.py").read_text()
    cli = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert "_MVPERF1_MAX_SCATTER_EDGES = 262_144" in selector
    assert "_select_and_update_reference" in selector
    assert "np.add.at" in selector
    assert "_deselect_and_update_reference" in repair
    assert "_shell_removal_scan" in repair
    assert 'execution_mode="optimized"' in cli
    assert 'stage_name="TARGET-DATA2C-MVSEL1/MVPERF1"' in cli
    assert 'stage_name="TARGET-DATA2C-REPAIR1/MVPERF1"' in cli


def test_mvperf1_benchmark_and_patch_notes_are_present():
    benchmark = ROOT / "benchmarks/benchmark_mlff_target_data2c_mvperf1.py"
    assert benchmark.is_file()
    evidence = json.loads((ROOT / "benchmarks/mlff_target_data2c_mvperf1_cloud_cpu_2026-08-16.json").read_text())
    assert evidence["decision_equivalent"] is True
    assert evidence["selector_speedup"] > 1.0
    assert evidence["scale_completed_16384"] is True
    scale32 = json.loads((ROOT / "benchmarks/mlff_target_data2c_mvperf1_scale32k_2026-08-16.json").read_text())
    assert scale32["k"] == 16384 and scale32["n"] == 32768
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.204a0.md").read_text()
    assert "TARGET-DATA2C-MVPERF1" in patch
    assert "16,384" in patch
