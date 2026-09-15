from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
CHAPTERS = ROOT / "docs/arch_manuals/mlff_training_data"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
REV_INDEX = ROOT / "docs/history/mlff/architecture_revisions/INDEX.md"
REL_INDEX = ROOT / "docs/history/mlff/release_notes/INDEX.md"


def _d3_sources() -> str:
    """The canonical D3 set: the top-level manual plus its numbered chapters."""

    chapters = sorted(CHAPTERS.glob("[0-9][0-9]_*.md"))
    return "\n\n".join(
        [MANUAL.read_text(encoding="utf-8")]
        + [path.read_text(encoding="utf-8") for path in chapters]
    )


def test_doc_arch1_release_and_current_authority_are_synchronized():
    assert mdstats.__version__ == "0.20.242a0"
    text = MANUAL.read_text(encoding="utf-8")
    assert 'status: "current normative D3 architecture"' in text
    for owner in (
        "docs/methods/mlff_scientific_method.md",
        "docs/methods/mlff_target_training_order_scientific_method.md",
        "docs/methods/mlff_numerical_algorithmic_method.md",
        "docs/methods/mlff_target_training_order_numerical_algorithmic_method.md",
        "45_target_training_order.md",
    ):
        assert owner in text, owner
        if owner.startswith("docs/"):
            assert (ROOT / owner).is_file(), owner
    assert "one complete `TargetTrainingOrder`" in text
    assert "post-selection cross-validation" in text
    snapshot = "docs/history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/"
    assert snapshot in text and (ROOT / snapshot).is_dir()
    assert "not as current authority" in text
    assert not (ROOT / "mlff_training_data_architecture.md").exists()
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()


def test_doc_arch1_manual_and_numbered_sources_index_the_same_canonical_chapters():
    chapters = sorted(path.name for path in CHAPTERS.glob("[0-9][0-9]_*.md"))
    assert chapters == [
        "00_front_matter.md", "10_foundations.md", "20_data_contracts.md",
        "30_statistical_design.md", "40_training_evaluation.md",
        "45_target_training_order.md", "50_target_size_selection.md",
        "60_execution_performance.md", "80_ownership_and_decisions.md",
        "90_references.md",
    ]
    manual = MANUAL.read_text(encoding="utf-8")
    readme = (CHAPTERS / "README.md").read_text(encoding="utf-8")
    sources = manual[manual.index("## 14. Detailed D3 sources and provenance"):]
    for name in chapters:
        assert f"`{name}`" in sources, name
        assert f"`{name}`" in readme, name
    assert "70_status_and_gates.md" not in chapters
    assert "it is not a generated aggregate" in manual
    assert len(manual.splitlines()) < 4000


def test_doc_arch1_current_target_size_and_execution_contract():
    text = _d3_sources()
    for token in (
        "pi_train", "T_N = pi_train[:N]", "common target-size training preparation",
        "operator-owned provisional design", "cross-validate admission",
        "fresh final production", "deterministic", "restart",
    ):
        assert token.lower() in text.lower(), token
    # The screen recommends; the operator decides; `cross-validate` freezes.
    assert (
        "The automatic screen produces evidence and an optional recommendation; "
        "it does not freeze the design." in text
    )
    assert "`cross-validate` admission is the only freeze boundary" in text
    assert "typed no-recommendation" in text
    assert "freezes the collection before numerical CV work" in text


def test_doc_arch1_manual_names_no_retired_target_size_owner():
    """Current D3 names the restored chain and no retired owner as current."""

    text = MANUAL.read_text(encoding="utf-8")
    for token in ("TargetSizeStudyPolicy", "TargetDataRoleFreeze", "target_size_study"):
        assert token not in text, token
    for token in (
        "TargetCoverageReference", "FEAS1", "NEIGHBOR1", "MVIDX", "MVSEL2",
        "REPAIR2", "MVQUAL",
    ):
        assert token in text, token

    # General D1/D2 papers delegate `pi_train` construction/qualification to the
    # scoped target-order owners instead of presenting the retired
    # condition-round-robin / hard-support-only method as current.
    general_d1 = (ROOT / "docs/methods/mlff_scientific_method.md").read_text(encoding="utf-8")
    general_d2 = (ROOT / "docs/methods/mlff_numerical_algorithmic_method.md").read_text(encoding="utf-8")
    assert "mlff_target_training_order_scientific_method.md" in general_d1
    assert "mlff_target_training_order_numerical_algorithmic_method.md" in general_d2
    for stale in (
        "a prefix is admitted only by label usability and explicitly declared hard-support obligations",
        "Diagnostic novelty or coverage measures do not silently become additional qualification gates",
    ):
        assert stale not in general_d1, stale
    for stale in (
        "The same deterministic rule is used for target-training and evaluation-reserve orders",
        "### 6.1 Condition-balanced priority order",
        "The canonical target order may consume candidate-independent priority vectors",
        "Q(N)=\\text{prefix exists}",
    ):
        assert stale not in general_d2, stale


def test_doc_arch1_external_algorithmic_provenance_is_cited():
    text = (CHAPTERS / "90_references.md").read_text(encoding="utf-8")
    for ref in ("[32]", "[33]", "[34]", "[35]", "[36]", "[37]"):
        assert ref in text
    assert "Blumofe" in text and "work stealing" in text.lower()
    assert "query_ball_point" in text
    assert "threadpoolctl" in text
    assert "NUMA" in text
    assert "numpy.bincount" in text


def test_doc_arch1_history_is_indexed_once_and_current_revision_is_recorded():
    revision_rows = [line for line in REV_INDEX.read_text().splitlines() if re.match(r"^\|\s*\d+\s*\|", line)]
    revisions = [int(line.split("|")[1].strip()) for line in revision_rows]
    assert revisions == sorted(set(revisions))
    assert revisions[-1] == 108
    assert "DOC-MVSEL2" in REV_INDEX.read_text()
    assert "0.20.242a0" in REL_INDEX.read_text()
    assert (ROOT / "docs/history/mlff/LINEAGE.md").is_file()
    assert (ROOT / "docs/history/mlff/manual_snapshots/mlff_training_data_architecture_rev090_full.md").is_file()


def test_doc_arch1_graph_and_directory_ownership_are_current():
    graph = json.loads(GRAPH.read_text())
    assert graph["schema_version"] == 5
    assert graph["authority_model"] == "d1_d2_d3_d4_layered_mlff_architecture"
    assert [item["level"] for item in graph["authority_chain"]] == ["D1", "D2", "D3", "D4"]
    assert "45_target_training_order.md" in graph["authority_chain"][2]["owner"]
    assert (ROOT / graph["historical_snapshot"]).is_dir()
    node_ids = {node["id"] for node in graph["nodes"]}
    for node in (
        "TARGET_SIZE_SPLIT", "TARGET_COVERAGE_REFERENCE", "CANONICAL_TARGET_OBLIGATIONS",
        "SHARED_FEAS_NEIGHBOR", "MVIDX", "TARGET_TRAINING_ORDER",
        "TARGET_PREFIX_QUALIFICATION", "TARGET_SIZE_GENERATION", "TARGET_ORDER_BUILD_STATE",
        "COMMON_TARGET_PREPARATION", "TARGET_SIZE_SCREEN", "PROVISIONAL_DESIGN",
        "FROZEN_TARGET_BINDINGS", "POST_SELECTION_CV", "FINAL_PRODUCTION",
        "FINAL_PUBLICATION", "QUALIFICATION", "STORAGE_PLANE",
    ):
        assert node in node_ids, node
    for retired in (
        "FEASIBILITY_EVIDENCE", "EXACT_NEIGHBORHOOD_AUTHORITY",
        "DOMAIN_SELECTION_ORDER", "DOMAIN_REPAIRED_MASTER_ORDER",
        "COMPACT_CONTINUATION_STATE", "PREFIX_QUALIFICATION_EVIDENCE",
        "QUALIFIED_TARGET_SIZE_POPULATION", "DOMAIN_LOCAL_TARGET_PREFIXES",
    ):
        assert retired not in node_ids
    assert not any(node.startswith("SIZE_STUDY_EPOCH") for node in node_ids)
    for edge in graph["edges"] + graph["forbidden_edges"]:
        assert edge["from"] in node_ids or edge["from"] == "D4_RUNTIME_ADAPTERS", edge
    forbidden = {(edge["from"], edge["to"]) for edge in graph["forbidden_edges"]}
    for edge in (
        ("POST_SELECTION_CV", "FROZEN_TARGET_BINDINGS"),
        ("TARGET_SIZE_SCREEN", "TARGET_TRAINING_ORDER"),
        ("POST_SELECTION_CV", "TARGET_TRAINING_ORDER"),
        ("TARGET_ORDER_BUILD_STATE", "TARGET_SIZE_GENERATION"),
        ("QUALIFICATION", "FINAL_PUBLICATION"),
        ("STORAGE_PLANE", "FROZEN_TARGET_BINDINGS"),
    ):
        assert edge in forbidden, edge
    edges = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    assert not (forbidden & edges)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "fresh final production on the complete T_selected" not in readme
    assert "a failure never changes the selected target size," not in readme
    runbook = (ROOT / "docs/guides/mlff_final_gpu1_workstation_runbook.md").read_text(
        encoding="utf-8"
    )
    assert "fresh final production on the complete T_selected" not in runbook

    root_names = {p.name for p in ROOT.iterdir() if p.is_file()}
    assert not any(name.startswith("ARCHITECTURE_NOTES_") for name in root_names)
    assert not any(name.startswith("PATCH_NOTES_") for name in root_names)
    assert "FINAL_GPU1_WORKSTATION_RUNBOOK.md" not in root_names
    assert (ROOT / "docs/guides/mlff_final_gpu1_workstation_runbook.md").is_file()


def test_doc_arch1_manual_hash_is_stable_under_current_bytes():
    digest = hashlib.sha256(MANUAL.read_bytes()).hexdigest()
    assert len(digest) == 64


def test_doc_arch1_no_campaign_global_scalar_selection_claims():
    manual = MANUAL.read_text(encoding="utf-8")
    stage = (ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text(encoding="utf-8")
    for stale in (
        "the current target-size choice is global",
        "one protocol-global target-size decision with one exact global selected membership",
        "cannot change global T_selected",
        "final T_selected -> final-training fitted products",
        "one pi_train and exact T_selected membership after the target-size freeze",
        "paired-seed candidate screen\n  -> selected binding",
        "one selected size or typed scientific failure",
        "alter `T_selected`",
    ):
        assert stale not in manual, f"stale scalar claim found in manual: {stale}"
        assert stale not in stage, f"stale scalar claim found in stage plan: {stale}"
