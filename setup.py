from __future__ import annotations

import sys

from setuptools import Extension, setup


def _mvsel2_extension() -> Extension:
    compile_args: list[str]
    link_args: list[str]

    if sys.platform.startswith("linux"):
        compile_args = [
            "-O3",
            "-fno-fast-math",
            "-ffp-contract=off",
            "-fopenmp",
        ]
        link_args = ["-fopenmp"]
    elif sys.platform == "win32":
        compile_args = ["/O2", "/fp:strict", "/openmp"]
        link_args = []
    else:
        # Build the exact serial backend on platforms where OpenMP is not part
        # of the default compiler toolchain. workers>1 will fail explicitly at
        # runtime rather than silently pretending to parallelize.
        compile_args = ["-O3", "-fno-fast-math", "-ffp-contract=off"]
        link_args = []

    return Extension(
        "mdstats._mvsel2_native",
        sources=["mdstats/_mvsel2_native.c"],
        extra_compile_args=compile_args,
        extra_link_args=link_args,
        optional=True,
    )


setup(ext_modules=[_mvsel2_extension()])
