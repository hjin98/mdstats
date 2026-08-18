from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DAG = ROOT / "docs" / "arch_manuals" / "stage11_dependency_graph.json"
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"

def test_revision46_contract_is_superseded_by_revision47_typed_graph():
    data=json.loads(DAG.read_text(encoding="utf-8"))
    assert data["architecture_revision"] >= 47
    assert data["schema_version"] == 2
    assert "Revision-47 authoritative typed dependency graph" in MANUAL.read_text(encoding="utf-8")
