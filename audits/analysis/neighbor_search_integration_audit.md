# S4 Periodic-Neighbor Integration Audit

## Release boundary

- Package: `mdstats`
- Version: `0.14.0`
- Stage: S4 - consumer integration, automatic policy, benchmarks, documentation, and release validation
- Scientific oracle: blocked dense minimum-image search
- Optimized rebuild backend: exact triclinic cell list
- Trajectory reuse: request-keyed fixed- or deformation-aware Verlet cache

S4 completes the staged S0-S4 neighbor-search program. It changes execution policy and provenance, not the scientific neighbor contract. Every returned accepted pair still satisfies the strict physical test

$$
r_{ij}<r_{\mathrm{cut}},
$$

with current-frame minimum-image vectors, distances, and original-cell image shifts.

## Implemented public policy

The new immutable public object is:

```python
NeighborSearchOptions(
    backend="auto",          # auto | dense | cell_list
    cache_mode="verlet",    # none | verlet
    skin=0.5,
    deformation_aware=True,
    dense_pair_threshold=32768,
    minimum_cache_frames=2,
    safety_tolerance=1.0e-12,
    max_cell_condition_number=1.0e12,
    fallback_to_dense=True,
    cell_list_options=CellListOptions(),
)
```

The automatic decision uses a deterministic estimate of dense pair work. It chooses dense below `dense_pair_threshold` and cell list at or above the threshold. The threshold is conservative, measured, recorded in provenance, and user-overridable.

Caching is activated only when all of the following hold:

1. the policy selects the cell-list backend;
2. `cache_mode="verlet"`;
3. the selected frame count is at least `minimum_cache_frames`;
4. the enlarged cutoff-plus-skin request is inside the exact unique-image regime.

A single-frame calculation therefore remains stateless even under the default high-level policy.

## Consumer integration

One analysis-local executor now serves:

- `compute_pair_rdf()`;
- `compute_coordination_distribution()`;
- `compute_bond_angle_distribution()`;
- `compute_atomic_connectivity()` for distance connectivity;
- hysteretic distance connectivity;
- reference distance connectivity.

Each public consumer accepts `neighbor_search_options`. Atomic connectivity also retains the earlier `verlet_cache_options` argument as a compatibility path. Passing both policy arguments is rejected rather than silently resolving an ambiguity.

Framework projection and ring analysis remain consumers of atomic-connectivity results. They do not own or duplicate cache state.

## Exact fallback behavior

S4 introduces no approximate fallback.

- If a requested Verlet list radius violates the unique-image construction limit, the executor disables caching for that request and evaluates an exact stateless cell list. The event is recorded as `verlet_list_radius_unsafe_to_stateless`.
- If an automatically chosen cell-list request exceeds configured exact-stencil complexity limits and `fallback_to_dense=True`, the executor switches that request to the dense oracle. The event is recorded as `cell_list_complexity_to_dense`.
- Explicitly forced unsupported cell-list requests still raise; automatic policy does not conceal a user override.

## Unified diagnostics

Every integrated result stores a JSON-compatible `metadata["neighbor_search"]` record with schema `mdstats.periodic-neighbor-search.v1`.

The record includes:

- requested, policy, and actually used backends;
- requested and selected cache modes;
- normalized request digests;
- estimated dense pair work;
- backend evaluation counts;
- candidate and accepted-pair counts;
- candidate efficiency;
- fallback events;
- cell-list rebuild and cache-reuse counts;
- mean and median frames per rebuild;
- rebuild-reason counts;
- interval-level minimum safety margins and singular values;
- the complete normalized high-level options.

The schema is stable when caching is inactive: rebuild counts and both mean and median interval statistics are reported as zero, while cache statistics are `None`.

## Correctness validation

Focused S4 integration suite:

```text
10 passed, 1 expected SparseBondAngleWarning
```

Focused fixed/deforming-cell Verlet suite:

```text
25 passed
```

Complete regression suite:

```text
282 passed, 25 expected warnings
```

Consumer-level tests compare final scientific observables, not only internal neighbor lists:

- RDF counts, $g(r)$, and cumulative coordination;
- per-atom/per-frame coordination matrices and distributions;
- angle counts, per-frame counts, and raw angles;
- distance, hysteretic, and reference connectivity state catalogs and frame-state identities.

Dense, stateless cell-list, and cached variable-cell modes agree exactly, except for the documented floating tolerance on reconstructed angles.

Additional acceptance coverage includes:

- deterministic automatic threshold selection;
- single-frame stateless behavior;
- unsafe-Verlet-radius fallback;
- automatic cell-list-complexity fallback;
- deterministic interval diagnostics;
- variable-cell deformation-aware reuse;
- independent-ensemble fallback;
- ill-conditioned-cell rejection;
- boundary crossings and adversarial omitted-pair cases inherited from S2-S3.

## Benchmark audit

The reproducible benchmark is:

```text
benchmarks/neighbor_search_benchmark.py
benchmarks/neighbor_search_benchmark.json
benchmarks/neighbor_search_benchmark.md
```

All benchmark comparisons passed exact scientific equivalence.

Representative measured results on the release environment:

| Workload | Atoms | Dense pair work | Cell-list speedup | Auto choice |
|---|---:|---:|---:|---|
| Small Na-LTA framework | 168 | 2,304 | 0.14x | dense |
| Replicated Na-LTA 2x2x1 | 672 | 36,864 | 3.66x | cell_list |
| Dense NaCl-like melt | 384 | 36,864 | 4.21x | cell_list |
| Mixed Na-LTA/salt interface | 552 | 41,472 | 1.47x | cell_list |
| Highly skewed binary cell | 384 | 36,864 | 2.65x | cell_list |

Trajectory reuse results:

| Workload | Frames | Cached speedup | Rebuilds | Reuse frames |
|---|---:|---:|---:|---:|
| Fixed-cell dense-salt trajectory | 8 | 2.63x | 1 | 7 |
| Variable-cell dense-salt trajectory | 8 | 2.94x | 1 | 7 |

These timings are machine-specific and are not universal guarantees. They support the conservative default threshold and demonstrate the intended scaling trend and amortized reuse benefit.

## Documentation audit

The normative production specification is maintained in both source and rendered form:

```text
docs/specs/analysis/neighbor_search_spec.md
docs/specs/analysis/neighbor_search_spec.pdf
```

Dependent RDF, coordination, bond-angle, connectivity, internal-neighbor, framework-topology, S2, S3, and staged-plan documents were synchronized. Ten affected PDFs, totaling 179 pages, passed preflight and complete rendered-page inspection. No clipping, overlap, broken glyph, malformed table, encryption, XFA form, or image-only page was observed.

## Release acceptance

S4 is complete when the following remain true:

1. dense search remains forceable and authoritative;
2. automatic policy selects only supported exact backends;
3. every fallback is exact and recorded;
4. single-frame and ensemble semantics are preserved;
5. consumer outputs remain backend-neutral;
6. cache intervals and rebuild reasons are deterministic;
7. Markdown and PDF specifications match source behavior;
8. the full suite, wheel/source builds, distribution-content audit, and installed-wheel smoke test pass.
