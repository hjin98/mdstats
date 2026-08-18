from pathlib import Path
import json
import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mvplan1_release_and_manual_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 65" in manual
    assert "TARGET-DATA2-MVPLAN1" in manual
    assert "128, 256, 512, 1024, 2048, 4096, 8192, 16384" in manual
    assert "8 -> 4 -> 2 -> 1" in manual
    assert "3 -> 10 -> 30" in manual
    assert "minimum hard-coverage qualifier requirement from three to **four**" in manual


def test_mvplan1_graph_freezes_ordered_roadmap_without_implementation_claim():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    nodes = {n["id"]: n for n in graph["nodes"]}
    plan = nodes["TARGET_DATA2_MVPLAN1_ROADMAP_FREEZE"]
    assert plan["implementation_status"] == "planned_frozen"
    assert plan["runtime_behavior_changed"] is False
    assert plan["planned_candidate_sizes"] == [128,256,512,1024,2048,4096,8192,16384]
    assert nodes["SIZE_HALVE2_EIGHT_CANDIDATE_FUNNEL"]["minimum_hard_qualifiers"] == 4
    assert nodes["TARGET_DATA2C_MVMIGRATE1_GENERATED_DEFAULT"]["fixed_generated_ceiling"] == 16384


def test_mvplan1_normative_spec_preserves_hard_coverage_and_current_runtime():
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2_mvplan1_multi_view_coverage_roadmap_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.198a0`" in spec
    assert "0.95 hard coverage" in spec
    assert "architecture freeze only" in spec
    assert "Revision-64 dynamic upper rescue remains current executable behavior" in spec
