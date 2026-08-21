from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any


@dataclass(frozen=True, slots=True)
class NativeExtensionSpec:
    """One in-tree compiled extension and its portable build requirements."""

    module: str
    sources: tuple[str, ...]
    strict_fp: bool = False
    openmp: bool = False
    optional: bool = True
    language: str | None = None


_NATIVE_EXTENSION_SPECS: tuple[NativeExtensionSpec, ...] = (
    NativeExtensionSpec(
        module="mdstats._mvsel2_native",
        sources=("mdstats/_mvsel2_native.c",),
        strict_fp=True,
        openmp=True,
        optional=True,
    ),
)


def registered_native_extension_specs() -> tuple[NativeExtensionSpec, ...]:
    """Return the canonical package-wide native extension registry."""

    return _NATIVE_EXTENSION_SPECS


def _platform_build_args(
    spec: NativeExtensionSpec,
) -> tuple[list[str], list[str]]:
    compile_args: list[str] = []
    link_args: list[str] = []

    if sys.platform == "win32":
        compile_args.append("/O2")
        if spec.strict_fp:
            compile_args.append("/fp:strict")
        if spec.openmp:
            compile_args.append("/openmp")
        return compile_args, link_args

    compile_args.append("-O3")
    if spec.strict_fp:
        compile_args.extend(["-fno-fast-math", "-ffp-contract=off"])

    if spec.openmp and sys.platform.startswith("linux"):
        compile_args.append("-fopenmp")
        link_args.append("-fopenmp")
    # On macOS and other POSIX platforms, do not assume an OpenMP runtime is
    # available from the default compiler. The extension is still built as an
    # exact serial backend and its runtime capability check reports OpenMP off.

    return compile_args, link_args


def _validate_registry(specs: tuple[NativeExtensionSpec, ...]) -> None:
    modules = [spec.module for spec in specs]
    if len(modules) != len(set(modules)):
        raise RuntimeError("mdstats native extension registry contains duplicate module names")
    for spec in specs:
        if not spec.module.startswith("mdstats."):
            raise RuntimeError(
                f"native extension {spec.module!r} must live inside the mdstats package"
            )
        if not spec.sources:
            raise RuntimeError(
                f"native extension {spec.module!r} has no registered source files"
            )


def build_native_extensions() -> list[Any]:
    """Materialize setuptools Extension objects for every registered target."""

    from setuptools import Extension

    specs = registered_native_extension_specs()
    _validate_registry(specs)
    extensions: list[Any] = []
    for spec in specs:
        compile_args, link_args = _platform_build_args(spec)
        extensions.append(
            Extension(
                spec.module,
                sources=list(spec.sources),
                extra_compile_args=compile_args,
                extra_link_args=link_args,
                optional=spec.optional,
                language=spec.language,
            )
        )
    return extensions
