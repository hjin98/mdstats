from pathlib import Path
import json


def test_perf_p2r_normative_spec_and_architecture_are_synchronized() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = (root / "docs/specs/training_data/mlff_perf_p2r_successive_fidelity_execution_spec.md").read_text()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())

    assert 'version: "0.20.241a0"' in spec
    assert "implementation-qualified; accelerator qualification deferred to FINAL-GPU1" in spec
    assert "coarse epoch candidates supplied by the calibration policy" in spec
    assert "authenticated content-addressed DATA8 fixed-file cache" in spec
    assert "must never repay" in spec
    assert "FINAL-GPU1" in spec
    assert "Jamieson" in spec and "Talwalkar" in spec
    assert "FIPS PUB 180-4" in spec

    assert "Exact continuation fidelity" in manual
    assert "successive-fidelity funnel" in manual
    assert "n1 < n2 < n3 <= n" in manual

    assert graph["schema_version"] == 2
    node_ids = {item["id"] for item in graph["nodes"]}
    assert {"COARSE_SCREEN", "SHORT_SCREEN", "FINAL_SCREEN", "FULL_TRAIN2_SCHEDULE"} <= node_ids
    assert not any(node.startswith("SIZE_STUDY_EPOCH") for node in node_ids)
