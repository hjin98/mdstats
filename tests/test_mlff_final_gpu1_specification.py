from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_final_gpu1_current_spec_runbook_and_policy_are_synchronized() -> None:
    root = _root()
    spec = (root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md").read_text()
    runbook = (root / "docs/specs/training_data/FINAL_GPU1_WORKSTATION_RUNBOOK.md").read_text()
    guide = (root / "docs/guides/mlff_final_gpu1_workstation_runbook.md").read_text()
    tool = (root / "tools/run_mlff_final_gpu_qualification.py").read_text()

    assert mdstats.__version__ == "0.20.242a0"
    assert mdstats.FINAL_GPU1_POLICY_SCHEMA == "mdstats.final-gpu1-policy.target-size-v5.v4"
    assert mdstats.FINAL_GPU1_QUALIFICATION_SCHEMA == "mdstats.final-gpu1-qualification.target-size-v5.v4"
    assert "mdstats.mlff-final-gpu1.preflight.target-size-v5.2026-08.v11" in tool
    assert "release-pinned preflight is the **v11** handoff contract" in runbook.lower()
    assert "current p6" in runbook.lower()
    assert "target-size-v5" not in spec.lower()
    assert "target-size-v5" not in runbook.lower()
    assert "select-target-size" in runbook
    assert "cross-validate" in runbook
    assert "train-production" in runbook

    policy = mdstats.FinalGpu1Policy()
    assert policy.required_pass_gates == mdstats.FINAL_GPU1_REQUIRED_PASS_GATES
    assert policy.measure_only_gates == mdstats.FINAL_GPU1_MEASURE_ONLY_GATES
    assert policy.optional_gates == mdstats.FINAL_GPU1_OPTIONAL_GATES
    assert policy.runtime_bound_gates == mdstats.FINAL_GPU1_RUNTIME_BOUND_GATES
    assert len(policy.required_pass_gates) == 8
    assert len(policy.measure_only_gates) == 6
    assert len(policy.optional_gates) == 2
    assert "16-item matrix" in spec
    assert "16-item matrix" in runbook
    assert guide == runbook

    for retired in (
        "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION",
        "TARGET_DATA2C_MVMIGRATE1_LEARNING_CONTROLS",
    ):
        assert retired not in policy.all_gates
    assert "are historical only" in spec
    assert "Do **not** run retired migration, rescue, or target-data activation commands" in runbook
    assert "keeps generated-default authorization false" in runbook




def test_final_gpu1_markdown_sources_exist() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md",
        root / "docs/specs/training_data/FINAL_GPU1_WORKSTATION_RUNBOOK.md",
        root / "docs/guides/mlff_final_gpu1_workstation_runbook.md",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 1_500, path
