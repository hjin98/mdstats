# Repository Guidelines

## Project Structure & Module Organization

The installable package is under `mdstats/`. Numerical routines live in `analysis/`; file readers and validation belong in `io/`; trajectory preparation is split between `preprocess/` and `coordinates/`. Plotting code is in `plotting/` and `graphics3d/`, while MLFF workflow code is in `training_data/`. Packaged JSON resources are stored in `mdstats/data/`. Tests mirror these areas in `tests/test_*.py`, with shared data and helpers in `tests/data/`, `tests/fixtures/`, and `tests/support/`. Specifications and release history live in `docs/`; runnable demonstrations, performance evidence, and reviews belong in `examples/`, `benchmarks/`, and `audits/`. Run commands from the project root (one level above this file).

## Build, Test, and Development Commands

- `python -m pip install -e .` installs an editable development copy.
- `python -m pip install ".[interactive,manifest]"` installs optional visualization and YAML support.
- `python -m pytest -q` runs the full suite with the configured `-ra` summary.
- `python -m pytest tests/test_msd.py -q` runs one focused module during iteration.
- `python -m pytest -m "not slow"` excludes external-runtime smoke tests.
- `python -m build` creates wheel and source distributions when the `build` package is available.

## Coding Style & Naming Conventions

Target Python 3.10 or newer. Use four-space indentation, PEP 8 names (`snake_case` functions/modules, `PascalCase` classes), type annotations, and short module or public-API docstrings. Follow nearby import and line-wrapping style; no repository-wide formatter or linter is configured, so avoid formatting-only churn. Prefix internal helpers with `_`. Preserve deterministic ordering, explicit units, array dtypes, immutable result contracts, and established numerical tolerances.

## Testing Guidelines

Pytest discovers `tests/test_*.py`; test functions should describe behavior, such as `test_minimum_image_unwrap_boundary_crossing`. Add focused regression coverage for every behavior change. Use `numpy.testing` for arrays and state `rtol`/`atol` explicitly when exact equality is inappropriate. Mark genuine external-runtime tests with `@pytest.mark.slow`; do not hide ordinary unit tests behind that marker.

## Commit & Pull Request Guidelines

This checkout does not expose Git history, but release notes use scoped, action-led summaries. Prefer concise imperative subjects such as `MSD: preserve fixed-origin semantics`. Keep commits narrowly focused. Pull requests should explain the problem, scientific or API invariants, affected modules, and exact tests run; link relevant issues or specifications. Include benchmark evidence for performance claims and screenshots only for visible plotting or 3D changes. Update `CHANGELOG.md` or owning documentation when public behavior changes.
