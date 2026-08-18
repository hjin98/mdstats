from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_size_halve2_release_public_surface_and_graph_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    assert mdstats.SIZE_HALVE2_VERSION == "mdstats.size-halve2.2026-08.v1"
    assert mdstats.SIZE_HALVE2_FIXED_TARGET_SIZES == (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    for name in (
        "SizeHalve2Policy", "SizeHalve2Plan", "build_size_halve2_plan",
        "with_size_halve2_epoch3_evidence", "with_size_halve2_epoch10_evidence",
        "with_size_halve2_epoch30_evidence", "build_size_halve2_execution_stage_plan",
        "validate_size_halve2_authority",
    ):
        assert hasattr(mdstats, name), name
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    node = next(v for v in graph["nodes"] if v["id"] == "SIZE_HALVE2_EIGHT_CANDIDATE_FUNNEL")
    assert node["implementation_status"] == "implemented_pre_migration_control_plane"
    assert node["implemented_release"] == "0.20.206a0"
    assert node["candidate_funnel"] == "q->min(q,4)->2->1"
    assert node["coverage_failing_training_forbidden"] is True
    assert node["production_authority_changed"] is False


def test_size_halve2_docs_freeze_qualified_only_3_10_30_contract():
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_size_halve2_fixed_eight_funnel_spec.md").read_text()
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.206a0.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert "revision 73" in manual
    assert "q -> min(q, 4)" in manual
    assert "coverage-failing" in manual.lower()
    assert "nonconverged_at_fixed_ceiling" in manual
    assert "**Gate:** `SIZE-HALVE2`" in spec
    assert "**Release:** `mdstats 0.20.206a0`" in spec
    assert "0->3" in spec and "3->10" in spec and "10->30" in spec
    assert "production TARGET-DATA2D authority" in spec
    assert "SIZE-HALVE2" in patch and "PERF-P2R" in patch
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")


def test_size_halve2_campaign_receipt_and_pre_migration_order_are_explicit():
    source = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert '"size_halve2_plan"' in source
    assert "_ensure_size_halve2_plan" in source
    prepare = source.index("target_multi_view_qualification = _ensure_target_multi_view_qualification")
    halve = source.index("_ensure_size_halve2_plan(", prepare)
    legacy = source.index("size_convergence = _ensure_target_size_convergence", halve)
    assert prepare < halve < legacy
    assert "production TARGET-DATA2D v2 unchanged" in source


def test_size_halve2_root_and_canonical_graph_mirrors_match():
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").is_file()
    assert not (ROOT / "mlff_training_data_architecture.md").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").is_file()
