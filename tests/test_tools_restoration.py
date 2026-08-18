from __future__ import annotations

import ast
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def test_source_tools_are_restored_and_packaged() -> None:
    expected = (
        TOOLS / "mdstats-mlff-campaign.py",
        TOOLS / "qualify_mace_runtime.py",
        TOOLS / "finalize_lta_data9a3_qualification.py",
        TOOLS / "performance" / "scan_interpreter_hotpaths.py",
    )
    for path in expected:
        assert path.is_file()
        assert path.stat().st_mode & 0o111
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "include campaign.toml.example" in manifest
    assert "recursive-include tools *" in manifest
    assert "recursive-include docs *.md *.pdf *.png *.json" in manifest
    assert "global-exclude *.py[cod]" in manifest


def test_campaign_example_tracks_current_optimized_backend_defaults() -> None:
    payload = tomllib.loads((ROOT / "campaign.toml.example").read_text(encoding="utf-8"))
    execution = payload["execution"]
    assert execution["inference_gpu_calibration_peak_trim_fraction"] == 0.05
    assert execution["parallel_inference_post_calibration_monitor_interval_seconds"] == 30.0
    assert execution["parallel_evaluation_prepare_jobs"] == 0
    assert execution["parallel_evaluation_finalize_jobs"] == 0
    assert execution["evaluation_pipeline_buffer_jobs"] == 0


def test_data9a3_finalizer_uses_current_production_plan_contract() -> None:
    path = TOOLS / "finalize_lta_data9a3_qualification.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    builders = [
        node for node in calls
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "build_production_corpus_qualification_record"
        )
    ]
    assert len(builders) == 1
    keywords = {kw.arg for kw in builders[0].keywords}
    assert "production_plan" in keywords
    assert "expected_source_count" not in keywords
    source = path.read_text(encoding="utf-8")
    assert "ProductionCorpusPlan" in source
    assert "require_foundation_features=False" in source
    assert "require_foundation_residual_e0=False" in source
    assert "require_data8_artifacts=False" in source
    assert "require_replay_corpus=False" in source


def test_source_checkout_tools_bootstrap_repository_imports() -> None:
    campaign = (TOOLS / "mdstats-mlff-campaign.py").read_text(encoding="utf-8")
    qualify = (TOOLS / "qualify_mace_runtime.py").read_text(encoding="utf-8")
    finalizer = (TOOLS / "finalize_lta_data9a3_qualification.py").read_text(encoding="utf-8")
    for source in (campaign, qualify, finalizer):
        assert 'Path(__file__).resolve().parents[1]' in source
        assert 'sys.path.insert(0, str(ROOT))' in source


def test_data9a3_finalizer_constructs_current_plan_dynamically() -> None:
    import importlib.util
    from types import SimpleNamespace

    from mdstats.training_data._common import digest

    path = TOOLS / "finalize_lta_data9a3_qualification.py"
    spec = importlib.util.spec_from_file_location("mdstats_data9a3_finalizer_tool", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = SimpleNamespace(content_digest=digest({"source": 1}))
    frames = SimpleNamespace(
        dataset_id="test-dataset",
        content_digest=digest({"frames": 1}),
    )
    data5 = SimpleNamespace(
        cross_validation_plans=(SimpleNamespace(folds=("a", "b", "c")),)
    )
    evidence = {
        "runs": [
            {
                "run_id": "run-1",
                "frame_count": 8,
                "reduced_formula": "AlNaO4Si",
                "ensemble": "nvt",
                "target_start_kelvin": 300.0,
                "target_end_kelvin": 300.0,
            }
        ]
    }
    plan = module._production_plan_for_data9a3(
        normalization={"normalization": 1},
        references={"reference": 1},
        evidence=evidence,
        source=source,
        frames=frames,
        data5=data5,
        expected_sources=1,
    )
    assert plan.dataset_id == "test-dataset"
    assert plan.expected_source_count == 1
    assert plan.expected_cross_validation_fold_count == 3
    assert plan.require_foundation_features is False
    assert plan.require_foundation_residual_e0 is False
    assert plan.require_data8_artifacts is False
    assert plan.require_replay_corpus is False
