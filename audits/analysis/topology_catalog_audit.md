# Topology Catalog Implementation Audit - mdstats 0.16.0

## Scope

This audit verifies the Stage 3 implementation in
`mdstats/analysis/topology_catalog.py` against:

- `docs/specs/analysis/topology_catalog_spec.{md,pdf}`;
- `docs/specs/analysis/atomic_connectivity_spec.{md,pdf}`;
- `docs/specs/analysis/framework_topology_spec.{md,pdf}`;
- `docs/arch_manuals/framework_ring_architecture.{md,pdf}`.

## Implemented public contract

The module exports immutable options, consistency/status enums, frame groups,
trajectory segments, transitions, catalogs, exceptions, schemas, and
`build_topology_catalog()` through both `mdstats.analysis` and `mdstats`.

Catalog mode:

- projects each referenced `AtomicConnectivityState` once;
- assigns exact topology classes by the Stage 2 structural key;
- uses digests only as nonauthoritative comparison buckets;
- stores deterministic first-occurrence topology IDs;
- stores frame groups for trajectories and ensembles;
- stores maximal segments and exact transitions only for trajectories.

Per-frame mode exposes one public topology record per selected frame and makes no
persistent cross-frame identity claim.

## Stage 2 identity review

Class identity includes the framework-topology schema, fixed mapping digest, PBC,
ordered retained vertices/species, and canonical `FrameworkEdgeKey` records.
It excludes traversal views, raw pre-gauge provenance, validation findings, and
projection diagnostics.

Therefore:

```text
A-O-S-B == B-S-O-A
A-O-S-B != A-S-O-B
```

Reverse discovery cannot create a false directed edge or false topology
transition. Changed asymmetric linker order remains structurally visible.

## Transition review

Each trajectory segment boundary records:

- source and target topology and connectivity-state IDs;
- selected-result positions, collection frame indices, and frame IDs;
- added and removed atomic edges when enabled;
- added and removed decorated framework edges when enabled;
- affected atom, framework-vertex, and linker-atom sets.

The persistence threshold labels short segments as `TRANSIENT`; it does not
smooth, remove, merge, or relabel frame assignments.

## Focused tests

The 26 Stage 3 tests cover:

- uniform and partitioned catalogs;
- recurring A-B-A topology identity;
- trajectory segments and descriptive persistence;
- ensemble grouping without temporal records;
- per-frame mode;
- optional transition-difference storage;
- asymmetric linker order and whole-path reversal;
- digest-collision protection by exact key comparison;
- source projection reuse and contextual errors;
- input and constructor invariants;
- serialization and digest tamper detection;
- variable-cell topology preservation;
- Na-LTA spectator-contact compression and controlled framework breakage.

## Validation result

```text
Ruff formatting:                         passed
Ruff lint:                               passed
Python compileall:                       passed
Focused topology-catalog tests:          26 passed
Complete regression suite:              322 passed
Expected warnings:                       27
Affected specification PDFs:             4 passed preflight
Rendered affected PDF pages inspected: 127
```

The expected warnings are existing sparse-statistics, visualization, and
velocity-reconstruction diagnostics. None indicates a topology-catalog error.

## Conclusion

The Stage 3 source, public exports, tests, architecture manual, and affected
module specifications agree. `primitive_ring.py` may now consume one exact
stored `FrameworkTopology` class at a time.
