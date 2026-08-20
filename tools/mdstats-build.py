#!/usr/bin/env python3
"""Install mdstats editable, compile every registered native target, and verify it.

This is the strict developer build command. Ordinary packaging remains standard
PEP-517/setuptools (`python -m pip install -e .`); this helper adds a fail-closed
post-install import check for every native extension registered by mdstats.
"""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import subprocess
import sys


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _native_modules(repo_root: Path) -> tuple[str, ...]:
    sys.path.insert(0, str(repo_root))
    try:
        from build_support.native_extensions import registered_native_extension_specs
        return tuple(spec.module for spec in registered_native_extension_specs())
    finally:
        try:
            sys.path.remove(str(repo_root))
        except ValueError:
            pass


def _install_command(repo_root: Path, *, no_deps: bool) -> list[str]:
    command = [sys.executable, "-m", "pip", "install", "-e", str(repo_root)]
    if no_deps:
        command.append("--no-deps")
    return command


def _verify_native_modules(modules: tuple[str, ...]) -> None:
    importlib.invalidate_caches()
    failures: list[str] = []
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")
            print(f"[FAIL] native target {module_name}: {exc}", flush=True)
        else:
            location = getattr(module, "__file__", None) or "<built-in>"
            print(f"[PASS] native target {module_name}: {location}", flush=True)
    if failures:
        joined = "\n  ".join(failures)
        raise RuntimeError("mdstats strict native build verification failed:\n  " + joined)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install mdstats in editable mode, build all registered native "
            "extensions, and fail if any registered native module cannot import."
        )
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="skip dependency installation when the active environment is already prepared",
    )
    args = parser.parse_args(argv)

    repo_root = _repository_root()
    modules = _native_modules(repo_root)
    print(f"[mdstats-build] repository={repo_root}", flush=True)
    print(
        "[mdstats-build] native-targets=" + (",".join(modules) if modules else "none"),
        flush=True,
    )

    command = _install_command(repo_root, no_deps=bool(args.no_deps))
    print("[mdstats-build] installing editable package and compiling native targets", flush=True)
    completed = subprocess.run(command, cwd=repo_root, check=False)
    if completed.returncode != 0:
        print(
            f"[FAIL] mdstats editable install/build exited {completed.returncode}",
            file=sys.stderr,
            flush=True,
        )
        return int(completed.returncode) or 1

    try:
        _verify_native_modules(modules)
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr, flush=True)
        return 1

    print(
        f"[PASS] mdstats build/install complete; native-targets={len(modules)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
