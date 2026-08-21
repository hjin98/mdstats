"""Repository-local build helpers for mdstats packaging.

This package is consumed by setuptools while building mdstats. It is not part of
the installed mdstats runtime package.
"""

from .native_extensions import (
    NativeExtensionSpec,
    build_native_extensions,
    registered_native_extension_specs,
)

__all__ = [
    "NativeExtensionSpec",
    "build_native_extensions",
    "registered_native_extension_specs",
]
