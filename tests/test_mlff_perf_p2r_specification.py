from pathlib import Path
import json


def test_perf_p2r_normative_spec_and_architecture_are_synchronized() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = (root / "docs/specs/training_data/mlff_perf_p2r_successive_fidelity_execution_spec.md").read_text()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())

    assert 'version: "0.20.184a0"' in spec
    assert "implementation-qualified; accelerator qualification deferred to FINAL-GPU1" in spec
    assert "coarse epoch candidates: 3, 4, 5" in spec
    assert "authenticated content-addressed DATA8 fixed-file cache" in spec
    assert "must never repay" in spec
    assert "FINAL-GPU1" in spec
    assert "Jamieson" in spec and "Talwalkar" in spec
    assert "FIPS PUB 180-4" in spec

    assert "revision 59" in manual
    assert "CPU/control-plane implementation qualified in `0.20.184a0`" in manual
    assert "PerfP2RParameterGrid" in manual
    assert "I(PERF-P2R)=implemented" in manual
    assert "PERF-P5" in manual

    assert graph["architecture_revision"] == 71
    assert graph["schema_version"] == 53
    node = next(item for item in graph["nodes"] if item["id"] == "PERF_P2R_SUCCESSIVE_FIDELITY_EXECUTION")
    assert node["implementation_status"] == "implemented_cpu_control_plane_deferred_final_gpu_qualification"
    assert node["qualification_schedule"] == "FINAL_GPU1"
    assert "authenticated_data8_fixed_file_cache" in node["cpu_control_plane_features"]
