from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mvmigrate1_release_surface_and_graph_are_synchronized():
    assert tuple(int(part) for part in mdstats.__version__.split("a", 1)[0].split(".")) >= (0, 20, 210)
    for name in (
        "TargetMultiViewMigrationPolicy", "TargetMultiViewLearningControlRow",
        "TargetMultiViewLearningControlReport", "TargetMultiViewMigrationPlan",
        "build_target_multi_view_migration_plan", "validate_target_multi_view_migration_plan",
        "build_migrated_target_data_ladder", "validate_migrated_target_data_ladder_authority",
    ):
        assert hasattr(mdstats, name), name
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] >= 77
    assert graph["schema_version"] >= 59
    node = next(v for v in graph["nodes"] if v["id"] == "TARGET_DATA2C_MVMIGRATE1_GENERATED_DEFAULT")
    assert node["implementation_status"] == "activation_transaction_implemented_final_gpu1_v2_pending"
    assert node["implemented_release"] == "0.20.208a0"
    assert node["fixed_target_sizes"] == [128, 256, 512, 1024, 2048, 4096, 8192, 16384]
    assert node["minimum_hard_qualifiers"] == 4
    assert node["retire_generated_dynamic_rescue"] is True
    assert node["generated_defaults_changed"] is False
    assert node["production_authority_changed"] is False
    assert node["next_gate"] == "FINAL-GPU1 workstation execution and explicit atomic activation"


def test_mvmigrate1_docs_freeze_atomic_gpu_deferred_migration_contract():
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2c_mvmigrate1_generated_policy_migration_spec.md").read_text()
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.209a0.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert "revision 75" in manual
    assert "TARGET-DATA2C v5 -> TARGET-DATA2D v3 -> TARGET-DATA2E v3" in manual
    assert "awaiting_final_gpu_qualification" in manual
    assert "gpu_qualification_status == \"passed\"" in manual
    assert "**Gate:** `TARGET-DATA2C-MVMIGRATE1`" in spec
    assert "**Release:** `mdstats 0.20.208a0`" in spec
    assert "CPU-only tests cannot synthesize activation authority" in spec
    assert "one SQLite transaction" in patch
    assert "## 0.20.210a0 - 2026-08-16" in changelog


def test_mvmigrate1_campaign_order_persists_latch_but_keeps_legacy_convergence_active():
    source = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert '"target_multi_view_migration_plan"' in source
    assert '"target_data_ladder_mv_candidate"' in source
    prepare = source.index("target_multi_view_qualification = _ensure_target_multi_view_qualification")
    halve = source.index("size_halve2_plan = _ensure_size_halve2_plan", prepare)
    fidelity = source.index("size_fidelity2_execution_plan = _ensure_size_fidelity2_execution_plan", halve)
    migrate = source.index("_ensure_target_multi_view_migration(", fidelity)
    legacy = source.index("size_convergence = _ensure_target_size_convergence", migrate)
    assert prepare < halve < fidelity < migrate < legacy
    assert "activation is fail-closed pending FINAL-GPU1" in source


def test_mvmigrate1_root_and_canonical_manual_graph_mirrors_match():
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").is_file()
    assert not (ROOT / "mlff_training_data_architecture.md").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").is_file()
