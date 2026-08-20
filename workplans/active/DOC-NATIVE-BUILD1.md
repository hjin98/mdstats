---
kind: implementation-workplan
workplan_id: DOC-NATIVE-BUILD1
protocol_version: 5.0.0
status: BUILD1_IN_PROGRESS
analysis_base_ref: feat/mvsel2-forward-lazy
---

# DOC-NATIVE-BUILD1 — uniform mdstats native build machinery

## Objective

Replace the one-off MVSEL2 extension build definition with one package-wide native build registry and one developer command that installs `mdstats`, compiles every registered native extension, and verifies that the compiled modules are importable.

The build machinery must remain ordinary Python packaging machinery: source/wheel builds and editable installs consume the same native registry. Scientific/runtime qualification remains owned by each subsystem and is not conflated with compilation success.

## Current state

`mdstats._mvsel2_native` is the first in-tree custom compiled extension. The current `setup.py` defines that extension directly, so future native kernels would otherwise accumulate ad-hoc build logic.

## Build contract

- `pyproject.toml` remains the PEP-517 package/build authority.
- `setup.py` becomes a thin setuptools bridge that consumes one central native-extension registry.
- A top-level build-support module owns platform/compiler profiles and all native target declarations.
- Future C/C++ CPU extensions are added by registering a target, not by modifying package-install commands.
- Normal development installation remains `python -m pip install -e .`; this compiles all registered native targets as part of installation.
- A strict helper command `python tools/mdstats-build.py` performs the editable install and then verifies imports for every registered native target. It fails if a registered target did not build, even if that target is optional for ordinary pure-Python package installation.
- Source distributions explicitly include native sources and build-support Python modules.
- Runtime capability/scientific parity checks remain separate. For example, successful import of `_mvsel2_native` does not by itself qualify its OpenMP numerical authority.

## Rebuild semantics

A rebuild is required when native sources, native build configuration/compiler flags, Python ABI/interpreter, compiler toolchain, or native dependency ABI/header inputs change. Pure Python-only package updates do not technically require recompilation.

Operationally, after pulling an arbitrary package update, rerunning the single build/install command is safe and removes the need for the user to determine whether that update touched native code.

## Gates

### BUILD1-G0 — central registry

Create a build-support registry with explicit extension specifications and reusable platform build profiles. Register the existing `mdstats._mvsel2_native` target without changing its strict-FP/OpenMP compiler semantics.

**Pass:** `setup.py` contains no target-specific compiler logic and obtains all `ext_modules` from the registry.

### BUILD1-G1 — one-command strict developer build

Add `tools/mdstats-build.py`.

The command must:

1. locate the repository root robustly;
2. invoke the active interpreter as `python -m pip install -e <repo>`;
3. use the same PEP-517/setuptools build path as ordinary installation;
4. verify that every registered native module imports after installation;
5. return nonzero if installation or native verification fails;
6. print the registered/built targets concisely.

No duplicate compiler invocation is allowed.

### BUILD1-G2 — packaging and regression contract

- Explicitly include build-support modules and native source/header files in the source distribution manifest.
- Add focused tests for registry uniqueness, source existence, setup delegation, and strict-build target discovery.
- Keep the native extension optional for ordinary installation so pure-Python fallback remains installable when a compiler is unavailable; the strict developer builder is the mechanism that requires all registered native targets.

### BUILD1-G3 — N3 handoff

Once the uniform build gate is source-complete, the MVSEL2 N3 workstation command uses `python tools/mdstats-build.py` instead of the one-off `python setup.py build_ext --inplace` step.

No MVSEL2 scientific code changes belong to BUILD1.
