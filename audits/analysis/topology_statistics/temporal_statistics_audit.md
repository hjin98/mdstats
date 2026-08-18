# TS3 Temporal Topology Statistics Audit

## Release

`mdstats 0.17.0a3`

## Scope

Implemented and reviewed:

```text
mdstats/analysis/topology_statistics/temporal.py
mdstats/analysis/topology_statistics/atomic.py
mdstats/analysis/topology_statistics/framework.py
docs/specs/analysis/topology_statistics/temporal_spec.{md,pdf}
docs/specs/analysis/topology_statistics/atomic_spec.{md,pdf}
docs/specs/analysis/topology_statistics/framework_spec.{md,pdf}
docs/specs/analysis/topology_statistics/_common_spec.{md,pdf}
docs/arch_manuals/topology_statistics_architecture.{md,pdf}
```

## API and architecture alignment

The code, public exports, specifications, and architecture manual agree on:

- `TemporalStatisticsOptions`;
- exact half-open `StateResidenceInterval` records;
- exact changed-boundary `StateTransitionEvent` records;
- state adjacency and changed-transition matrices;
- per-state dwell distributions and return lags;
- cumulative changed-boundary counts;
- generic `EntityPresenceEpisode` and `EntityPresenceStatistics` records;
- trajectory-only semantics and explicit ensemble rejection;
- gauge-invariant atomic-contact identities and canonical framework-edge identities;
- sample-span duration and censoring conventions;
- schema-checked serialization and SHA-256 payload digests.

TS3 does not reconstruct connectivity, project framework graphs, infer Markov rates,
or assign independent-sample uncertainty. Atomic and framework modules retain ownership
of their entity identities and use the shared temporal kernel only after catalog
identity has been established.

## Focused validation

The combined TS0--TS3 focused suite passed **61 tests**. TS3 coverage includes:

- exact residence intervals and event boundaries;
- adjacency matrices with self-boundaries and changed matrices with zero diagonal;
- return frame and physical-time lags;
- single-frame and uniform trajectories;
- direct ensemble rejection;
- entity-presence episodes and left/right censoring;
- optional temporal-output suppression;
- custom quantile propagation;
- immutable arrays;
- canonical serialization and digest-tampering rejection;
- atomic-contact integration;
- framework-edge integration.

## Complete regression

The complete package suite passed **383 tests** with **27 expected warnings** and
zero failures. Ruff formatting, Ruff lint, and Python compilation passed.

## Real Na-LTA acceptance

The serialized 2,000-frame, 300 K Na-LTA catalogs produced:

### Atomic connectivity

- 72 unique states;
- 72 residence intervals;
- 71 changed-state boundaries;
- mean dwell length 27.7777777778 frames;
- median dwell length 24 frames;
- maximum dwell length 101 frames;
- 324 distinct gauge-invariant atomic contacts;
- 342 contact-presence episodes.

### Framework topology

- one topology class;
- one 2,000-frame residence interval;
- zero changed-state boundaries;
- 96 canonical framework edges;
- one full-window episode for every framework edge.

This verifies that TS3 resolves Na-contact timing while preserving the uniform
framework-topology conclusion.

## Documentation validation

Affected PDFs:

- temporal specification: 14 pages;
- common specification: 16 pages;
- atomic specification: 19 pages;
- framework specification: 13 pages;
- topology-statistics architecture manual: 23 pages.

Total: **85 pages**. Every PDF passed structural preflight and rendered-page visual
inspection without clipping, overlap, or broken mathematical glyphs.

## Distribution validation

The wheel contains the TS3 temporal module and updated atomic/framework modules but
no documentation payload. The source distribution contains the module, focused
tests, paired specifications, architecture manual, and this audit. An isolated
installed-wheel smoke test reproduced exact trajectory intervals and the Na-LTA
atomic/framework temporal contrast outside the source tree.
