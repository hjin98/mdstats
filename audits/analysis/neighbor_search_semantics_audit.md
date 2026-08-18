# S4.1 Semantics-Aware Cache Policy Audit

## Release boundary

- Package: `mdstats`
- Version: `0.14.1`
- Scope: conservative high-level cache resolution for trajectories, ensembles, and single-frame selections
- Low-level fixed-cell and deformation-aware Verlet correctness rules: unchanged

## Motive

A stateless cell list is valid for every frame collection. Verlet reuse is stateful and is only likely to be useful when consecutive configurations are geometrically related. Independent ensembles do not guarantee that relation. The previous high-level default attempted caching for every eligible multi-frame cell-list request, which remained exact but could rebuild a larger-radius list on every ensemble frame.

Version `0.14.1` makes the high-level decision depend on declared frame semantics while preserving an explicit expert override.

## Public policy

```python
NeighborSearchOptions(
    backend="auto",     # auto | dense | cell_list
    cache_mode="auto", # auto | none | verlet
    skin=0.5,
    deformation_aware=True,
    dense_pair_threshold=32768,
    minimum_cache_frames=2,
    max_consecutive_zero_reuse_rebuilds=3,
)
```

Automatic cache resolution is:

| Selected collection | `cache_mode="auto"` |
|---|---|
| One selected frame | Stateless |
| Time-ordered trajectory | Verlet when the cell-list backend and geometric constraints permit it |
| Independent ensemble | Stateless |

`cache_mode="verlet"` remains an expert override. It requests scientifically safe cache attempts, not a performance guarantee.

## Runtime shutoff

A request-local cache interval begins at a build and ends at the next rebuild. The initial build is not counted as a failed interval. A completed interval with no successful reuse increments a counter; any successful reuse resets it. At the configured limit, the executor disables caching for the remainder of that request and returns to a stateless cell list at the physical cutoff.

Default rule:

```text
3 consecutive completed intervals with zero reuse
    -> repeated_zero_reuse_to_stateless
```

The shutoff does not weaken geometric correctness and does not modify the low-level cache validity criterion.

## Diagnostics

The high-level diagnostic schema is `mdstats.periodic-neighbor-search.v2`. It records:

- resolved frame semantics;
- requested and selected cache modes;
- cache-resolution reasons;
- runtime cache-disable state and reason;
- consecutive zero-reuse count and configured limit;
- exact fallback events;
- inherited backend, candidate, rebuild, reuse, margin, and singular-value statistics.

A runtime-disabled request reports `cache_mode_selected="verlet_then_none"` and `cache_disable_reason="repeated_zero_reuse"`.

## Consumer integration

The shared policy is used by:

- pair RDF;
- coordination distributions;
- bond-angle distributions;
- distance connectivity;
- hysteretic connectivity;
- reference connectivity.

No consumer independently reinterprets trajectory or ensemble semantics.

## Acceptance results

```text
Python compileall:                         passed
Ruff full-tree formatting:                 passed
Ruff full-tree lint:                       passed
Focused policy/integration suite:          17 passed, 3 expected warnings
Focused low-level Verlet suite:            25 passed
Complete regression suite:                 289 passed, 27 expected warnings
Nine revised Markdown/PDF specifications:  preflight and visual inspection passed
```

Focused tests cover:

- trajectory automatic cache eligibility;
- ensemble and single-frame automatic statelessness;
- explicit fixed-cell ensemble reuse;
- conservative variable-cell ensemble rebuilds;
- repeated-zero-reuse shutoff;
- reset of the shutoff counter after successful reuse;
- identical RDF, coordination, angle, and connectivity outputs under automatic and forced-stateless ensemble execution.

## Deferred tuning

This release intentionally does not implement:

- automatic skin optimization;
- automatic bin-scale optimization;
- velocity-, timestep-, or fluctuation-based cost models;
- ensemble geometric probing or clustering;
- frame reordering;
- online performance retuning;
- persistent hardware-specific tuning profiles.

The implemented policy is a robust near-term correction, not a general autotuner.
