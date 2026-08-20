from __future__ import annotations

from setuptools import setup

from build_support.native_extensions import build_native_extensions


setup(ext_modules=build_native_extensions())
