from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from build_support import native_extensions


ROOT = Path(__file__).resolve().parents[1]


def _load_build_tool():
    path = ROOT / "tools" / "mdstats-build.py"
    spec = importlib.util.spec_from_file_location("mdstats_build_tool", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_registry_is_unique_and_sources_exist() -> None:
    specs = native_extensions.registered_native_extension_specs()
    modules = tuple(spec.module for spec in specs)
    assert modules
    assert len(modules) == len(set(modules))
    assert "mdstats._mvsel2_native" in modules
    for spec in specs:
        assert spec.module.startswith("mdstats.")
        assert spec.sources
        for source in spec.sources:
            assert (ROOT / source).is_file(), source


def test_mvsel2_native_registry_preserves_exact_openmp_profile() -> None:
    spec = next(
        item
        for item in native_extensions.registered_native_extension_specs()
        if item.module == "mdstats._mvsel2_native"
    )
    assert spec.strict_fp is True
    assert spec.openmp is True
    assert spec.optional is True


def test_setup_py_delegates_all_native_targets_to_registry() -> None:
    source = (ROOT / "setup.py").read_text(encoding="utf-8")
    assert "build_native_extensions" in source
    assert "_mvsel2_extension" not in source
    assert "Extension(" not in source
    assert "-fopenmp" not in source


def test_manifest_carries_build_support_and_native_sources() -> None:
    source = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include build_support *.py" in source
    assert "recursive-include mdstats *.c *.cc *.cpp *.cxx *.h *.hpp" in source


def test_strict_build_tool_discovers_registry_and_uses_active_python() -> None:
    tool = _load_build_tool()
    expected = tuple(
        spec.module for spec in native_extensions.registered_native_extension_specs()
    )
    assert tool._native_modules(ROOT) == expected

    command = tool._install_command(ROOT, no_deps=False)
    assert command == [sys.executable, "-m", "pip", "install", "-e", str(ROOT)]

    no_deps = tool._install_command(ROOT, no_deps=True)
    assert no_deps == command + ["--no-deps"]


def test_strict_build_tool_cleans_stale_objects_and_binary(tmp_path: Path) -> None:
    tool = _load_build_tool()
    package = tmp_path / "mdstats"
    package.mkdir()
    stale = package / "_example.cpython-test.so"
    source = package / "_example.c"
    build_object = tmp_path / "build" / "temp" / "example.o"
    build_object.parent.mkdir(parents=True)
    build_object.write_bytes(b"old-object")
    stale.write_bytes(b"old-binary")
    source.write_text("/* source */\n", encoding="utf-8")

    assert tool._native_artifacts(tmp_path, "mdstats._example") == (stale,)
    tool._clean_native_build_state(tmp_path, ("mdstats._example",))
    assert not stale.exists()
    assert not (tmp_path / "build").exists()
    assert source.exists()
