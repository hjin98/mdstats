from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli
from mdstats.training_data import model_features
from mdstats.training_data import evaluation_views

ROOT = Path(__file__).resolve().parents[1]


def test_opt_eval3_release_identity_and_documentation() -> None:
    # OPT-EVAL3 remains part of the frozen 0.20.99 MLFF scientific identity even
    # when later execution-only package releases advance mdstats.__version__.
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    assert model_features.MACE_MONITOR_GRAPH_CACHE_SCHEMA == "mdstats.mace-monitor-graph-cache.v1"
    assert evaluation_views.EVALUATION_DATASET_VIEW_SCHEMA == "mdstats.evaluation-dataset-view.v1"
    spec = ROOT / "docs/specs/training_data/mlff_opt_eval3_monitor_graph_view_cache_spec.md"
    manual = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
    assert spec.is_file()
    spec_text = spec.read_text()
    manual_text = manual.read_text()
    for required in (
        "persistent cache root",
        "single-flight",
        "immutable",
        "0.20.99a0",
        "OPT-EVAL4",
    ):
        assert required in spec_text
    assert "OPT-EVAL3 - monitor-level graph and immutable evaluation-view caching - implemented in 0.20.99a0" in manual_text
    assert "OPT-EVAL1 through OPT-CTRL1 is complete" in manual_text


def test_lta_density_example_multiformat_update_is_in_release_tree() -> None:
    example = (ROOT / "examples/plot_lta_mixed_alkali_density.py").read_text()
    assert "--lammps-type-map" in example
    assert "lammps-dump" in example
    assert "read_lammps_frames" in example
