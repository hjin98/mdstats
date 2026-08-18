# TS1 Atomic-Connectivity Statistics Audit

## Scope

```text
mdstats/analysis/topology_statistics/atomic.py
docs/specs/analysis/topology_statistics/atomic_spec.{md,pdf}
docs/arch_manuals/topology_statistics_architecture.{md,pdf}
tests/test_topology_statistics_atomic.py
```

## Implemented contract

TS1 derives immutable descriptive statistics from completed
`AtomicConnectivityResult` objects without rebuilding connectivity. It provides:

- exact total-edge and species-pair contact PMFs;
- frame/sample-aligned scalar series;
- state occupancy, Shannon entropy, and effective state count;
- gauge-invariant atom-pair contact occupancy;
- per-species degree PMFs and per-atom population moments;
- trajectory-only aggregate contact additions/removals;
- schema-checked serialization and SHA-256 result digests.

Periodic image shifts are intentionally excluded from persistent cross-state
contact identity. This matches the authoritative atomic catalog transition policy
and prevents periodic gauge changes from creating false contact events.

## Focused validation

```text
TS0 common tests: 22 passed
TS1 atomic tests: 14 passed
Combined focused: 36 passed
```

Coverage includes constant and variable PMFs, zero-contact requests, exact contact
occupancy, degree statistics, recurrent state occupancy, trajectory aggregate
changes, ensemble semantics, optional outputs, custom quantiles, immutable arrays,
serialization, digest tampering, and periodic-gauge invariance.

## Real Na-LTA validation

The serialized 2,000-frame 300 K Na-LTA atomic catalog produced:

```text
Frames:                    2000
Unique connectivity states: 72
Si-O count:                96 in all frames
Al-O count:                96 in all frames
Na-O support:              110 through 121
Na-O mean:                 115.8735
Na-O population SD:        2.8563084129694394
Changed frame boundaries:  71
Gauge-invariant additions: 40
Gauge-invariant removals:  31
```

All additions and removals belong to the Na-O pair. The invariant Si-O and Al-O
counts agree with the previous framework validation.

## Complete regression

```text
Complete package suite: 358 passed
Expected warnings:       27
```

The suite was executed in four deterministic node-ID groups because the single
combined command exceeded the execution window. Every collected test was included
exactly once.

## Static validation

```text
Ruff format check: passed
Ruff lint check:   passed
Python compileall: passed
Installed-wheel Na-LTA smoke test: passed
Wheel/source content audits: passed
```

## Documentation validation

```text
atomic_spec.pdf:                          19 pages
_common_spec.pdf:                         16 pages
topology_statistics_architecture.pdf:    23 pages
Total inspected:                         58 pages
PDF structural preflight:                passed
Rendered-page inspection:                passed
```

## Result

TS1 is accepted as the atomic-connectivity statistics layer. TS2 may build the
framework-topology statistics branch on the same TS0 foundation.
