---
kind: implementation-workplan
workplan_id: DOC-NATIVE-BUILD1
protocol_version: 5.0.0
status: BUILD1_SOURCE_COMPLETE_WORKSTATION_VALIDATION_PENDING
analysis_base_ref: feat/mvsel2-forward-lazy
---

# DOC-NATIVE-BUILD1 — uniform mdstats native build machinery

## Objective

Replace the one-off MVSEL2 extension build definition with one package-wide native build registry and one developer command that installs `mdstats`, compiles every registered native extension, and verifies that the compiled modules are importable.

The build machinery remains ordinary Python packaging machinery: source/wheel builds and editable installs consume the same native registry. Scientific/runtime qualification remains owned by each subsystem and is not conflated with compilation success.

## Current state

`mdstats._mvsel2_native` is the first in-tree custom compiled extension. The original one-off target-specific `setup.py` implementation has been replaced by the uniform machinery described here.

## Build contract

- `pyproject.toml` remains the PEP-517 package/build authority.
- `setup.py` is a thin setuptools bridge that consumes one central native-extension registry.
- `build_support/native_extensions.py` owns native target declarations and reusable platform/compiler requirements.
- Future C/C++ CPU extensions are added by registering a target, not by modifying package-install commands.
- Normal development installation remains `python -m pip install -e .`; this compiles all registered native targets as part of installation.
- The strict developer command `python tools/mdstats-build.py` performs a clean editable install/build and then verifies imports for every registered native target. It fails if a registered target did not build, even if that target is optional for ordinary pure-Python package installation.
- Before a strict build, the generated `build/` tree and stale in-tree binary artifacts for registered modules are removed so old object files or an obsolete `.so`/`.pyd` cannot mask a failed/current-profile rebuild.
- Verification occurs in a fresh Python subprocess so newly installed editable-package path metadata is honored.
- Source distributions explicitly include build-support modules and native C/C++ source/header files.
- Runtime capability/scientific parity checks remain separate. For example, successful import of `_mvsel2_native` does not by itself qualify its OpenMP numerical authority.

## Rebuild semantics

A rebuild is required when native sources, native build configuration/compiler flags, Python ABI/interpreter, compiler toolchain, or native dependency ABI/header inputs change. Pure Python-only package updates do not technically require recompilation.

Operationally, after pulling an arbitrary package update, rerunning the single strict build/install command is safe and removes the need for the user to determine whether that update touched native code. The strict command intentionally clean-rebuilds registered native targets so compiler-profile changes cannot reuse stale object files.

For a normal source checkout:

```text
python tools/mdstats-build.py
```

For an already-prepared environment where dependency installation should be skipped:

```text
python tools/mdstats-build.py --no-deps
```

## Gate status

| Gate | Status | Result / next boundary |
|---|---|---|
| BUILD1-G0 | IMPLEMENTED | Central native registry added; `setup.py` now delegates all extension declarations. |
| BUILD1-G1 | IMPLEMENTED | One-command strict clean editable install/build/import verification added. |
| BUILD1-G2 | IMPLEMENTED; SOURCE TESTS PENDING | Sdist manifest explicitly carries build support and native sources; focused registry/build-tool regressions added. |
| BUILD1-G3 | READY | MVSEL2 N3 should use `python tools/mdstats-build.py` instead of direct `setup.py build_ext`. |

## Implemented sequence

- `d8c1dede08451998d587568d86481dc59212e725` — add BUILD1 workplan;
- `354df85bf1e71012bc6d956bade9291bf9a18388` / `1035df98f6412b6817cb1ab3632371a44ad53d08` — add build-support package and native registry;
- `46bbda5b7713fcf7f1ee6214621e3a88beb03b30` — reduce `setup.py` to registry delegation;
- `d7b2e4f1a387aa88eadd6f7563dbddfd39101f20` — add strict one-command developer build;
- `57dda06663b2310dd7704dce6cc8c1ce2f2c61d9` — make native/build sources explicit in sdist;
- `c9e384510dbb610894d35af9c2d947895e1ec3a8` / `4a8dfeb57a81c1fdd1eb6d86cf0039096fe2f158` — add focused build-registry regressions;
- `8f327c07dbadafbca166c46658eb3db960ec2c02` — harden strict build against stale binaries and in-process editable-path ambiguity;
- `2d1e92570b68a77443eacea499ecaab8bc4d7bc9` — force clean strict rebuild by clearing generated build objects;
- `b0d6c998f6876aa6facbdd6f0db1823b6be97561` — cover clean-object/binary behavior in focused regressions.

## BUILD1-G0 — central registry

The registry entry for `mdstats._mvsel2_native` retains the original build semantics:

- strict FP enabled;
- OpenMP requested where the default platform toolchain supports the established flags;
- Linux: `-O3 -fno-fast-math -ffp-contract=off -fopenmp`, link `-fopenmp`;
- Windows: `/O2 /fp:strict /openmp`;
- other POSIX/macOS: exact serial build without assuming an OpenMP runtime;
- extension remains optional for ordinary package installation.

## BUILD1-G1 — strict developer build

The strict helper performs one compiler/install path only:

1. read registered native module names;
2. remove the generated `build/` tree and stale in-tree binaries matching those module names;
3. invoke the active interpreter as `python -m pip install -e <repo>`;
4. start fresh Python subprocesses to import every registered native module;
5. fail if installation or any registered-module import fails.

This does not duplicate compilation and does not replace standard PEP-517 packaging.

## BUILD1-G2 — remaining validation

On the source checkout, run:

```text
python -m pytest -q tests/test_native_build_registry.py tests/test_mlff_mvsel2_native_backend.py
python tools/mdstats-build.py --no-deps
```

The second command is the real build qualification and should report the registered native target and a `[PASS]` import location.

## BUILD1-G3 — N3 handoff

After BUILD1 validation, the MVSEL2 N3 workstation sequence begins with:

```text
python tools/mdstats-build.py --no-deps
```

then runs the MVSEL2 runtime qualifier/focused tests and product meter. No direct `python setup.py build_ext --inplace` step is part of the supported workflow anymore.

No MVSEL2 scientific code changes belong to BUILD1.
