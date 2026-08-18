# TS0 Common Topology-Statistics Foundation Audit

## Scope

This audit covers:

```text
mdstats/analysis/topology_statistics/_common.py
docs/specs/analysis/topology_statistics/_common_spec.{md,pdf}
docs/arch_manuals/topology_statistics_architecture.{md,pdf}
tests/test_topology_statistics_common.py
```

## Implemented contract

The TS0 implementation provides graph-independent:

- exact nonnegative integer probability mass functions;
- population scalar summaries using `ddof=0`;
- dense catalog-state occupancy and Shannon diversity;
- trajectory-only disjoint visit counts;
- ensemble-safe non-temporal occupancy;
- immutable frame/sample axes and scalar series;
- deterministic state-to-frame expansion;
- schema-checked serialization and stable payload digests.

The module contains no atomic-edge, framework-edge, bridge, ring, site, or cage
interpretation.

## Focused validation

```text
TS0 focused tests: 22 passed
```

Coverage includes exact delta distributions, tied modes, population standard
deviation, constant series, recurrent trajectory visits, ensemble semantics,
unobserved declared states, entropy, axis validation, read-only arrays,
state expansion, serialization, schema rejection, and deterministic digests.

## Complete regression

```text
Complete package suite: 344 passed
Expected warnings:       27
```

The warning set is unchanged and consists of established scientific or
visualization warnings.

## Static validation

```text
Ruff format check: passed
Ruff lint check:   passed
Python compileall: passed
```

## Documentation validation

```text
_common_spec.pdf:                       15 pages
 topology_statistics_architecture.pdf: 23 pages
PDF structural preflight:              passed
Rendered-page inspection:              passed
```

The specification and implementation expose the same public classes, functions,
input constraints, semantics, and serialization schema.

## Result

TS0 is accepted as the common foundation for later atomic, framework, temporal,
and combined topology-statistics stages.
