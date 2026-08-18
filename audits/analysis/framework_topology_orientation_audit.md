# Stage 2.1 whole-path orientation repair audit

## Scope

This repair corrects projected framework path identity before Stage 3 topology
catalog implementation.

The authoritative model is now:

```text
undirected projected adjacency
+
orientation-aware ordered atomic-path decoration
```

A complete path and its complete reverse are one edge class:

```text
A-O-S-B == B-S-O-A
```

An endpoint-fixed linker-order swap is different:

```text
A-O-S-B != A-S-O-B
```

## Source changes

- `FrameworkPathRule` now stores one endpoint/linker/endpoint pattern.
- Endpoint entries may be exact atomic numbers or `None` wildcards.
- Canonicalization compares the whole signature with its whole reverse.
- Rule-overlap detection compares complete oriented signatures.
- Terminal path matching evaluates endpoint species and linker order together.
- Version-1 endpoint-pair payloads are rejected because their orientation cannot
  be recovered unambiguously.
- `OrientedFrameworkEdgePath` provides canonical and reverse traversal views.
- Reverse traversal reverses atom order and linker order, reverses and negates
  atomic edge-image shifts, and negates projected translations.
- NetworkX and visualization adapters expose canonical/reverse path metadata
  while retaining `directed=False`.

## Schema changes

```text
mdstats.framework-mapping.v2
mdstats.framework-topology.v2
mdstats.framework-topology-graph-view.v2
mdstats.framework-topology-path-view.v2
```

## Focused scientific tests

The focused tests verify:

1. `Si-O-S-Al` is accepted.
2. `Al-S-O-Si` is accepted as the complete reverse.
3. `Si-S-O-Al` is rejected by the first rule.
4. The two asymmetric endpoint-fixed patterns may coexist as distinct rules.
5. Reverse declarations have identical mapping identity.
6. Reverse traversal transforms all path and periodic data together.
7. Version-1 endpoint-pair serialization is rejected explicitly.
8. Projected and atomic-path visualization metadata retain both path signatures.
9. Existing symmetric T-O-T and T-O-O-T behavior is unchanged.
10. The relaxed Na-LTA integration fixture remains 48 vertices and 96 edges.

## Validation

```text
Focused framework and visualization suite: 29 passed, 3 expected warnings
Complete regression suite:                 296 passed, 27 expected warnings
Ruff formatting:                           passed
Ruff lint:                                 passed
Python compileall:                         passed
PDF preflight:                             passed for 4 revised documents
Rendered-page inspection:                  passed for 111 pages
```

The warnings are existing sparse-sampling or visualization diagnostics. No
warning indicates a topology mismatch or path-orientation failure.

## Stage boundary

Stage 3 may now classify exact version-2 framework topologies. It must compare
canonical decorated edge records rather than bare unordered endpoint pairs.
Primitive-ring traversal must consume the `+1/-1` oriented edge view.
