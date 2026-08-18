# TS2 Framework Topology Statistics Audit

## Release

`mdstats 0.17.0a2`

## Scope

Implemented and reviewed:

```text
mdstats/analysis/topology_statistics/framework.py
docs/specs/analysis/topology_statistics/framework_spec.md
docs/specs/analysis/topology_statistics/framework_spec.pdf
docs/arch_manuals/topology_statistics_architecture.md
docs/arch_manuals/topology_statistics_architecture.pdf
```

## API/specification alignment

The public module, package re-exports, and specification agree on:

- `FrameworkStatisticsOptions`;
- `FrameworkBridgeSignature`;
- graph-descriptor, endpoint-pair, bridge-signature, degree, edge-occupancy, and
  transition-aggregate result objects;
- `FrameworkTopologyStatistics`;
- `compute_framework_topology_statistics(...)`;
- source-schema and digest provenance;
- trajectory versus ensemble behavior;
- whole-path reversal equivalence;
- the warning that `E - V + C` is graph cycle-space rank, not ring count.

No duplicate public export names were found. The mirrored module/spec paths exist in
both Markdown and PDF form.

## Focused validation

The TS0--TS2 focused suite passed 50 tests. TS2-specific coverage includes:

- exact descriptor PMFs and frame series;
- topology occupancy;
- endpoint-species and complete bridge signatures;
- degree statistics;
- canonical projected-edge occupancy;
- aggregate additions/removals and affected atoms;
- ensemble semantics;
- parallel projected edges;
- asymmetric linker order and complete reverse equivalence;
- per-frame catalog mode;
- optional-output disabling;
- serialization, digest tampering, and read-only arrays.

## Complete regression

The test tree was executed in four file groups:

- 83 passed, 7 expected warnings;
- 89 passed, 14 expected warnings;
- 69 passed, 3 expected warnings;
- 131 passed, 3 expected warnings.

Total: **372 passed, 27 expected warnings, 0 failures**.

Ruff format, Ruff lint, and Python compilation passed.

## Real Na-LTA acceptance

The serialized 2,000-frame 300 K Na-LTA framework catalog produced:

- one topology class;
- 48 framework vertices in every frame;
- 96 projected edges in every frame;
- one connected component;
- zero isolated vertices;
- graph cycle-space rank 49;
- 96 Al--Si endpoint edges;
- 96 Al--O--Si bridges under rule `T-O-T`;
- degree four for every Al and Si vertex;
- occupancy one for all 96 canonical projected edges;
- no framework transition aggregate.

An installed-wheel smoke test reproduced these results outside the source tree.

## Documentation validation

- framework TS2 specification: 13 pages;
- topology-statistics architecture manual: 23 pages;
- both PDFs passed structural preflight;
- all rendered pages were visually inspected with no clipping, overlap, or broken
  mathematical glyphs.

## Distribution audit

- wheel contains `mdstats/analysis/topology_statistics/framework.py` and no
  documentation payload;
- source distribution contains the module, paired specification, architecture
  manual, focused test, and this audit;
- installed-wheel Na-LTA smoke test passed.
