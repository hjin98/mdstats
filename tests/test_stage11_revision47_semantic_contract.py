from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "stage11_site_kinetics_architecture.md"
DAG = ROOT / "docs" / "arch_manuals" / "stage11_dependency_graph.json"
SPEC = ROOT / "docs" / "specs" / "documentation" / "stage11_revision47_provenance_kinetic_pmf_dag_spec.md"

REQUIRED_TYPES = {"source_identity_requires", "execution_requires", "promotion_requires"}


def data():
    return json.loads(DAG.read_text(encoding="utf-8"))


def required_graph(d):
    nodes = {n["id"] for n in d["nodes"]}
    req = {n: set() for n in nodes}
    for e in d["edges"]:
        if e["type"] in REQUIRED_TYPES and not (e["type"] == "promotion_requires" and "predicate" in e and e.get("conditional", False)):
            req[e["to"]].add(e["from"])
    return req


def ancestors(req, node):
    out=set(); stack=list(req[node])
    while stack:
        cur=stack.pop()
        if cur in out: continue
        out.add(cur); stack.extend(req[cur])
    return out


def edges(d, *, to=None, type=None):
    out=d["edges"]
    if to is not None: out=[e for e in out if e["to"]==to]
    if type is not None: out=[e for e in out if e["type"]==type]
    return out


def test_revision47_typed_graph_is_acyclic_and_source_bound():
    d=data(); assert d["schema_version"] == 2; assert d["architecture_revision"] >= 47
    req=required_graph(d)
    for n in req:
        assert n not in ancestors(req,n), n
    assert {e["from"] for e in edges(d,to="SOURCE_BYTES",type="source_identity_requires")} == {"SOURCE_BUNDLE"}
    assert {e["from"] for e in edges(d,to="SOURCE_COORDINATES",type="source_identity_requires")} == {"SOURCE_BUNDLE"}
    assert {"source_identity_requires","execution_requires","promotion_requires","conditional_requires","optional_enrichment","optional_verification","supersedes","replay_triggers"} <= set(d["edge_type_definitions"])


def test_revision47_pmf_and_thermodynamic_verification_are_not_overgated():
    d=data()
    dens={e["from"] for e in edges(d,to="PMF_DENSITY")}
    force={e["from"] for e in edges(d,to="PMF_FORCE")}
    assert "E3B" not in dens
    assert "E3B" in force
    assert {e["from"] for e in edges(d,to="PMF_CROSSCHECK",type="execution_requires")} == {"PMF_DENSITY","PMF_FORCE"}
    assert all(e["type"] == "conditional_requires" for e in edges(d,to="THERMO4A") if e["from"] in {"THERMO1","THERMO2","PMF_DENSITY","PMF_FORCE","PMF_CROSSCHECK"})


def test_revision47_kinetic_crossfit_and_zero_event_edges():
    d=data()
    assert {"KSAMP0","E7A"} <= {n["id"] for n in d["nodes"]}
    assert "KSAMP0" in {e["from"] for e in edges(d,to="F0")}
    assert "KSAMP0" in {e["from"] for e in edges(d,to="E9B")}
    assert "E7A" in {e["from"] for e in edges(d,to="F0")}
    assert any(e["type"] == "replay_triggers" and e["from"] == "E9B" and e["to"] == "G0" for e in d["edges"])


def test_revision47_product_gates_and_freeze_ownership():
    d=data(); txt=MANUAL.read_text(encoding="utf-8")
    basin_geom={e["from"] for e in edges(d,to="E8B_BASIN_GEOMETRY")}
    basin_thermo={e["from"] for e in edges(d,to="E8B_BASIN_THERMO")}
    assert "THERMO4A" not in basin_geom
    assert "THERMO1" in basin_thermo
    assert any(e["from"]=="THERMO4A" and e["type"]=="optional_verification" for e in edges(d,to="E8B_BASIN_THERMO"))
    assert "E8B_PATH" in {n["id"] for n in d["nodes"]}
    assert "E8B_TRANSITION_STATE" in {n["id"] for n in d["nodes"]}
    assert "GR4 alone owns" in txt or "GR4 alone" in txt
    assert "ThermodynamicResultProvenance" in txt
    assert "source_qualified_unverified" in txt
    assert "KineticCrossfitPartition" in txt
    assert "RateCandidateEdgeUniverse" in txt
    assert SPEC.stat().st_size > 3000


def test_revision47_manual_has_no_stale_revision_or_partition_contract():
    text=MANUAL.read_text(encoding="utf-8"); flat=re.sub(r"\s+"," ",text)
    assert "Revision-47 authoritative typed dependency graph" in text
    assert "Revision-45 terminology" not in text
    assert "Revision-46 authoritative dependency graph" not in text
    assert "thermodynamic_estimation" in text and "thermodynamic_validation" in text
    assert "kinetic_model_fit" in text and "kinetic_model_validation" in text
    assert "Stage 11E5a is implemented in" not in text
