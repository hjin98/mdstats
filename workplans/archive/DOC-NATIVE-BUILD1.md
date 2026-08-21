---
kind: implementation-workplan
workplan_id: DOC-NATIVE-BUILD1
protocol_version: 5.0.0
status: DONE
analysis_base_ref: feat/mvsel2-forward-lazy
closed_at: 2026-08-20
---

# DOC-NATIVE-BUILD1 — uniform mdstats native build machinery

## Objective

Replace the one-off MVSEL2 extension build definition with one package-wide native build registry and one developer command that installs `mdstats`, compiles every registered native extension, and verifies that the compiled modules are importable.

The build machinery remains ordinary Python packaging machinery: source/wheel builds and editable installs consume the same native registry. Scientific/runtime qualification remains owned by each subsystem and is not conflated with compilation success.

## Final state

`mdstats._mvsel2_native` is the first in-tree custom compiled extension. The original one-off target-specific `setup.py` implementation has been replaced by uniform package build machinery and clean PEP-517 validation is complete.

The accepted build contract is:

- `pyproject.toml` remains the PEP-517 package/build authority;
- `build_support/native_extensions.py` is the single native-extension registry and compiler-profile owner;
- `setup.py` is a thin setuptools bridge that loads that canonical registry by source path, so isolated PEP-517 bootstrap does not require the project package to be importable first;
- future C/C++ CPU extensions are added by registering a target rather than inventing a target-specific install command;
- normal development installation remains `python -m pip install -e .`;
- the strict developer command `python tools/mdstats-build.py` performs a clean editable install/build and verifies imports for every registered native target;
- stale build objects and in-tree native binaries are removed before strict builds so an obsolete artifact cannot mask a failed current build;
- source distributions explicitly contain build-support modules and native C/C++ source/header inputs;
- native compilation/import success remains distinct from subsystem numerical/runtime qualification.

## Rebuild semantics

A rebuild is required when native sources, native build configuration/compiler flags, Python ABI/interpreter, compiler toolchain, or native dependency ABI/header inputs change. Pure Python-only updates do not technically require recompilation.

Operationally, after pulling an arbitrary package update, rerunning:

```text
python tools/mdstats-build.py
```

is the canonical strict build/install path. In a prepared environment where dependency installation should be skipped:

```text
python tools/mdstats-build.py --no-deps
```

## Gate closeout

| Gate | Final status | Evidence |
|---|---|---|
| BUILD1-G0 | PASS | Central registry owns all native targets and compiler semantics. |
| BUILD1-G1 | PASS | One-command clean editable install/build/import verification works from a clean checkout. |
| BUILD1-G2 | PASS | Focused build/native regressions pass; source distribution builds and contains the registry plus native C source. |
| BUILD1-G3 | PASS | MVSEL2 product runtime uses the standardized build and the independently qualified native/OpenMP backend. |

## Clean-validation finding and correction

The first clean Ubuntu/Python 3.11 validation was intentionally run from a fresh GitHub Actions checkout rather than an already-prepared workstation environment.

Run `32430628159` failed during isolated PEP-517 requirements discovery before native compilation. The failure was:

```text
ModuleNotFoundError: No module named 'build_support'
```

Root cause: the then-current `setup.py` used a direct Python import of `build_support.native_extensions`. During isolated PEP-517 bootstrap the project source tree is not guaranteed to be importable as an installed package, so a clean build could fail even though an existing source/workstation environment had already qualified the compiled runtime.

The owning packaging boundary was fixed rather than weakening validation:

- `665b2d1aadefde3487676640fa0a343a2b73e903` — load the canonical native registry from its source path with `runpy.run_path`, preserving one registry while removing bootstrap import dependence;
- `1c85d31eca799bad9dd08163884dd0690fecefff` — add regression coverage forbidding a direct `build_support` bootstrap import and retaining all existing registry/build-tool checks.

The same clean validator was then rerun as GitHub Actions run `32430735582`, job `96621605881`, and passed every step:

1. clean checkout on Ubuntu with Python 3.11;
2. strict `python tools/mdstats-build.py` build/install/import verification;
3. `qualify_mvsel2_native_backend_v2()` with native backend available, qualified, and OpenMP enabled;
4. focused `tests/test_native_build_registry.py` and `tests/test_mlff_mvsel2_native_backend.py` regressions;
5. source-distribution construction;
6. verification that the sdist contains `build_support/native_extensions.py` and `mdstats/_mvsel2_native.c`.

This closes the reproducible clean-build claim.

## Relationship to G4-N3 qualification

BUILD1 validation is deliberately narrower and different from the already-completed MVSEL2 G4-N3 product qualification.

G4-N3 proved the compiled native/OpenMP backend's exact runtime behavior, real-MVIDX scaling, fallback policy, and product performance on the actual workstation/campaign path. BUILD1 proves that a clean source checkout can reproducibly **create** that native extension through the supported package build path and that source distributions carry the required build inputs.

Both are now complete. No additional workstation rerun is required merely to close BUILD1.

## Historical implementation sequence

- `d8c1dede08451998d587568d86481dc59212e725` — add BUILD1 workplan;
- `354df85bf1e71012bc6d956bade9291bf9a18388` / `1035df98f6412b6817cb1ab3632371a44ad53d08` — add build-support package and native registry;
- `46bbda5b7713fcf7f1ee6214621e3a88beb03b30` — reduce `setup.py` to registry delegation;
- `d7b2e4f1a387aa88eadd6f7563dbddfd39101f20` — add strict one-command developer build;
- `57dda06663b2310dd7704dce6cc8c1ce2f2c61d9` — make native/build sources explicit in sdist;
- `c9e384510dbb610894d35af9c2d947895e1ec3a8` / `4a8dfeb57a81c1fdd1eb6d86cf0039096fe2f158` — add focused build-registry regressions;
- `8f327c07dbadafbca166c46658eb3db960ec2c02` — harden strict build against stale binaries and in-process editable-path ambiguity;
- `2d1e92570b68a77443eacea499ecaab8bc4d7bc9` — force clean strict rebuild by clearing generated build objects;
- `b0d6c998f6876aa6facbdd6f0db1823b6be97561` — cover clean-object/binary behavior in focused regressions;
- `665b2d1aadefde3487676640fa0a343a2b73e903` / `1c85d31eca799bad9dd08163884dd0690fecefff` — close the isolated PEP-517 bootstrap gap discovered by final clean validation.

## Closure

BUILD1 is complete and archived. The package-wide native registry/build command is accepted infrastructure. Future native extensions should reuse this mechanism unless materially different requirements such as substantial shared C++ libraries, CUDA/HIP, or a more complex cross-target build graph justify a separately reviewed backend migration.
