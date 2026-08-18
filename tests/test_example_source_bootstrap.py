"""Direct-launch import-path tests for top-level example scripts."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


EXAMPLE_NAMES = (
    "plot_lta_mixed_alkali_density.py",
    "plot_na_lta_300k_all_species_density.py",
)


def _execute_bootstrap(script: Path, *, reported_file: Path) -> dict[str, object]:
    source = script.read_text(encoding="utf-8")
    prefix, marker, _ = source.partition("from ase.data import chemical_symbols")
    assert marker, "Example bootstrap must run before the first third-party import."
    namespace: dict[str, object] = {
        "__file__": str(reported_file),
        "__name__": "example_bootstrap_test",
    }
    exec(compile(prefix, str(script), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_direct_example_launch_prefers_adjacent_source_tree(name: str) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    script = repository_root / "examples" / name
    original_path = list(sys.path)
    try:
        namespace = _execute_bootstrap(script, reported_file=script)
        assert namespace["SOURCE_TREE_ROOT"] == repository_root
        assert sys.path[0] == str(repository_root)
        assert (Path(sys.path[0]) / "mdstats" / "__init__.py").is_file()
    finally:
        sys.path[:] = original_path


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_copied_example_uses_installed_package_path(
    name: str, tmp_path: Path
) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    script = repository_root / "examples" / name
    copied_path = tmp_path / name
    copied_path.write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
    original_path = list(sys.path)
    try:
        namespace = _execute_bootstrap(script, reported_file=copied_path)
        assert namespace["SOURCE_TREE_ROOT"] is None
        assert sys.path == original_path
    finally:
        sys.path[:] = original_path
