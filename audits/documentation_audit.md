# Documentation Consistency Audit - mdstats 0.17.0a1

## Revised normative documents

TS1 is synchronized across:

1. `docs/specs/analysis/topology_statistics/atomic_spec.{md,pdf}`;
2. `docs/specs/analysis/topology_statistics/_common_spec.{md,pdf}`;
3. `docs/arch_manuals/topology_statistics_architecture.{md,pdf}`.

The source `atomic_connectivity_spec` was reviewed and requires no scientific API
change because TS1 is a read-only consumer of `AtomicConnectivityResult`.

## Shared contract

All documents and source agree that:

- the atomic catalog is authoritative;
- TS1 never rebuilds or changes connectivity;
- integer counts use exact PMFs;
- state descriptors are evaluated once per unique state;
- cross-state contact identity is the gauge-invariant atom pair;
- image-shift-only changes do not create contact events;
- degree PMFs are weighted by state frame occupancy;
- trajectory aggregate changes are allowed, while ensembles remain non-temporal;
- exact event timelines and lifetimes are deferred to TS3;
- atomic contacts are not automatically chemical bonds or site hops;
- result arrays, metadata, schemas, and digests are immutable and validated.

## API agreement

The TS1 specification matches the implemented public API:

```text
AtomicStatisticsOptions
AtomicContactKey
AtomicContactOccupancy
AtomicPairContactStatistics
AtomicSpeciesDegreeStatistics
AtomicPairTransitionCount
AtomicTransitionAggregateStatistics
AtomicConnectivityStatistics
compute_atomic_connectivity_statistics
```

## PDF validation

```text
Atomic statistics specification:       19 pages
Common foundation specification:       16 pages
Topology statistics architecture:      23 pages
Total inspected:                       58 pages
```

All PDFs passed structural preflight and rendered-page inspection. No clipping,
overlap, missing glyphs, or broken equations were observed.
