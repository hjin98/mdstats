# TS4 Combined Topology Statistics Audit

Release: `mdstats 0.17.0a4`

## Scope

This audit covers:

- `mdstats/analysis/topology_statistics/combined.py`;
- public exports through `mdstats.analysis.topology_statistics`, `mdstats.analysis`, and `mdstats`;
- `docs/specs/analysis/topology_statistics/combined_spec.{md,pdf}`;
- the revised topology-statistics architecture manual;
- `tests/test_topology_statistics_combined.py`;
- the serialized 2,000-frame 300 K Na-LTA acceptance case.

## Implemented contract

TS4 validates exact atomic/framework source alignment and derives:

- atomic-state/framework-class frame contingency;
- row- and column-conditional state composition;
- atomic-to-framework compression ratio;
- stable, atomic-only, framework-only, and coupled boundary categories;
- a compact cross-layer regime and neutral interpretation;
- immutable schema-versioned combined serialization.

The implementation does not rebuild graph states, infer mechanisms, or treat ensemble order as time.

## Alignment checks

The implementation rejects mismatches in:

- frame semantics;
- selected collection frame indices;
- frame IDs or ordering;
- frame-to-connectivity-state assignments;
- state-to-topology coverage;
- representative topology source digests.

Boundary interpretation is disabled for ensembles and unreconciled per-frame identity modes.

## Validation

- TS0--TS4 focused tests: **71 passed**;
- complete package tests: **393 passed**;
- expected warnings: **27**;
- Ruff formatting and lint: passed;
- Python compilation: passed;
- schema round trip and digest tampering rejection: passed;
- paired PDF preflight and rendered-page inspection: passed.

## Na-LTA acceptance

The production catalogs produced:

- 72 atomic states;
- 1 framework class;
- compression ratio 72;
- 1,928 stable boundaries;
- 71 atomic-only boundaries;
- 0 framework-only boundaries;
- 0 coupled boundaries.

The automatic interpretation is:

```text
atomic connectivity varies while framework topology remains uniform
```

## Consistency review

The code, combined specification, TS0--TS3 dependency specifications, architecture manual, README, changelog, and public exports use the same:

- exact alignment contract;
- state/class namespaces;
- boundary labels;
- non-temporal ensemble policy;
- per-frame identity limitation;
- schema version `mdstats.topology-statistics.combined.v1`.
