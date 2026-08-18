# Topology Statistics Plotting Audit

Release: `mdstats 0.17.0a5`

Scope:

- `mdstats/plotting/topology_statistics.py`;
- `docs/specs/plotting/topology_statistics_spec.{md,pdf}`;
- TS5 plotting exports through `mdstats.plotting` and `mdstats`;
- the 2,000-frame 300 K Na-LTA example.

Validated behavior:

- exact integer contact-count PMF bars use stored support and probabilities;
- pair-count series use the stored `FrameAxis` and completed scalar series;
- catalog occupancy and assignment plots use exact state/class IDs;
- transition rasters, transition matrices, and dwell PMFs require TS3 temporal output;
- framework descriptor plots use TS2 descriptor series without recomputation;
- cross-layer plots use TS4 contingency and boundary objects;
- functions return Matplotlib `(Figure, Axes)` and do not call `show()` or write files;
- PNG, SVG, and PDF save paths passed focused tests;
- ensemble axes remain sample-index axes and are not assigned transition semantics.

Na-LTA output:

- 12 PNG figures and 12 matching PDF figures generated;
- Na-O count support 110-121, mean 115.8735, population SD 2.8563;
- flat Si-O and Al-O count PMFs at 96;
- flat framework edge count at 96;
- 1,928 stable, 71 atomic-only, zero framework-only, and zero coupled boundaries.

Validation:

- focused TS5 tests: 5 passed;
- complete package suite: 398 passed, 27 expected warnings;
- Ruff format/lint and Python compilation passed;
- plotting specification PDF preflight and rendered-page inspection passed.
