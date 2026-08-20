from __future__ import annotations

from pathlib import Path
import runpy

from setuptools import setup


# PEP-517 executes setup.py in an isolated bootstrap environment where the
# project source tree is not guaranteed to be importable as a package yet.
# Load the canonical native registry by source path so requirements discovery
# and editable/wheel builds use the same registry without requiring an
# already-installed mdstats/build_support package.
_registry = runpy.run_path(
    str(Path(__file__).resolve().parent / "build_support" / "native_extensions.py")
)
setup(ext_modules=_registry["build_native_extensions"]())
