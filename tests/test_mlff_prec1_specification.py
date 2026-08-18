from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_staged_precision_profiles_spec.md"
GRAPH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json"


def test_prec1_release_and_architecture_status() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    manual = MANUAL.read_text(encoding="utf-8")
    spec = SPEC.read_text(encoding="utf-8")
    assert "PREC1 - precision profiles, explicit staged schedule, and init realization - implemented in 0.20.108a0" in manual
    assert "PREC1 implemented in mdstats 0.20.108a0" in spec
    assert "The post-0.20.105 evaluation, precision, and storage implementation roadmap is complete." in manual
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34


def test_prec1_public_contract_is_exported() -> None:
    for name in (
        "PrecisionProfile",
        "PrecisionStage",
        "PrecisionSchedulePolicy",
        "ResolvedPrecisionStage",
        "ResolvedPrecisionSchedule",
        "canonical_precision_schedule_policy",
        "legacy_one_stage_precision_policy",
    ):
        assert hasattr(mdstats, name)
