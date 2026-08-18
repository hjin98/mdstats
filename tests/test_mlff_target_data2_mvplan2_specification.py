from pathlib import Path
import json
import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mvplan2_release_and_manual_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 66" in manual
    assert "TARGET-DATA2-MVPLAN2" in manual
    assert "full-pool self-coverage is not a support-feasibility authority" in manual.lower()
    assert "q -> min(q, 4)" in manual
    assert "Coverage-failing target sizes are never trained" in manual
    assert "StageResourceScope" in manual
    assert "stable frame UID" in manual


def test_mvplan2_graph_freezes_optimized_plan_without_runtime_migration():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    assert graph["documentation_gate"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION"
    nodes = {n["id"]: n for n in graph["nodes"]}
    plan = nodes["TARGET_DATA2_MVPLAN2_OPTIMIZATION_FREEZE"]
    assert plan["implementation_status"] == "planned_frozen"
    assert plan["runtime_behavior_changed"] is False
    assert plan["fixed_generated_ceiling"] == 16384
    assert nodes["TARGET_DATA2B_FEAS1_FULL_POOL_FEASIBILITY"]["implementation_status"] == "implemented_diagnostic_only"
    assert nodes["TARGET_DATA2B_FEAS1_FULL_POOL_FEASIBILITY"]["full_pool_self_coverage_role"] == "consistency_only"
    assert nodes["TARGET_DATA2C_MVIDX1_COVERAGE_INDEX"]["exact_sparse_bidirectional_graph"] is True
    assert nodes["TARGET_DATA2C_MVSEL1_PROGRESSIVE_SELECTOR"]["gain_accumulation"] == "FP64"
    assert nodes["TARGET_DATA2C_REPAIR1_DEFICIT_EXCHANGE"]["replacement_rank_inheritance"] is True
    assert nodes["SIZE_HALVE2_EIGHT_CANDIDATE_FUNNEL"]["candidate_funnel"] == "q->min(q,4)->2->1"
    assert nodes["TARGET_DATA2C_MVMIGRATE1_GENERATED_DEFAULT"]["runtime_behavior_changed_only_here"] is True


def test_mvplan2_normative_spec_preserves_current_runtime_and_hard_authority():
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2_mvplan2_optimized_multi_view_coverage_roadmap_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.199a0`" in spec
    assert "16,384 is a hard ceiling" in spec
    assert "hard coverage remains 0.95" in spec
    assert "Revision-64 dynamic rescue remains executable until MVMIGRATE1" in spec
    assert "Coverage-failing sizes are never trained" in spec
