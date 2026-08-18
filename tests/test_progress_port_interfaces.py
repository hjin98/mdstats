"""Regression checks for the package-wide progress-port interface."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from mdstats import plot_framework_dynamics_3d, prepare_framework_dynamics_scene
from mdstats.plotting.atomic_density import prepare_atomic_density_fields


def test_long_running_density_interfaces_expose_progress_port() -> None:
    for function in (
        prepare_framework_dynamics_scene,
        plot_framework_dynamics_3d,
        prepare_atomic_density_fields,
    ):
        parameters = inspect.signature(function).parameters
        assert "progress" in parameters
        assert parameters["progress"].kind is inspect.Parameter.KEYWORD_ONLY
        assert "progress_callback" in parameters


def test_lta_examples_use_package_progress_port_not_local_reporter() -> None:
    repository = Path(__file__).resolve().parents[1]
    for relative in (
        "examples/plot_lta_mixed_alkali_density.py",
        "examples/plot_na_lta_300k_all_species_density.py",
    ):
        source = (repository / relative).read_text()
        tree = ast.parse(source)
        class_names = {
            node.name for node in tree.body if isinstance(node, ast.ClassDef)
        }
        assert "ProgressReporter" not in class_names
        assert "TextProgressPort" in source
        assert "ProgressEmitter" in source
        assert "progress=progress_port" in source
