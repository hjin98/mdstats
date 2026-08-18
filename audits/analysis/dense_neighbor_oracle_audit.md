# Stage S0 dense-oracle audit

## Release scope

- Package version: `0.14.0a0`
- Stage: `S0 - Dense oracle and baseline harness`
- Optimized cell-list behavior enabled: **no**
- Verlet caching enabled: **no**
- Scientific cutoff and minimum-image semantics changed: **no**

## Implemented source changes

- `mdstats/analysis/_neighbors.py`
  - explicit `NeighborSearchBackend.DENSE` facade selection;
  - dedicated `_build_dense_neighbor_list()` oracle implementation;
  - backend provenance in `NeighborListResult`;
  - defensive read-only result arrays;
  - unchanged strict cutoff, MIC, image-shift, pair-counting, and CSR semantics.
- `mdstats/analysis/_neighbor_compare.py`
  - canonical center/row sorting;
  - exact CSR, atom-pair, and image-shift comparison;
  - tolerance-bounded vector and distance comparison;
  - structured mismatch diagnostics and assertion helper.
- `tests/support/neighbor_cases.py`
  - stored-seed orthogonal, triclinic, mixed-PBC, and boundary fixtures;
  - independent scalar pair-loop reference.
- `tests/test_neighbor_oracle.py`
  - block-size invariance, repeated-run determinism, strict cutoff,
    immutable arrays, canonical ordering, and mismatch diagnostics.
- `benchmarks/dense_neighbors_benchmark.py`
  - reproducible timing and `tracemalloc` peak-memory baseline.

## Source API facts

- `NeighborSearchBackend` values: `[('DENSE', 'dense')]`
- `NeighborListResult` fields: `['frame_index', 'center_indices', 'neighbor_indices', 'offsets', 'vectors', 'distances', 'image_shifts', 'cutoff', 'pair_counting', 'backend']`
- `build_neighbor_list` parameters: `['collection', 'frame_index', 'center_indices', 'candidate_neighbor_indices', 'cutoff', 'pair_counting', 'backend', 'block_size']`
- `iter_neighbor_lists` parameters: `['collection', 'frame_indices', 'center_indices', 'candidate_neighbor_indices', 'cutoff', 'pair_counting', 'backend', 'block_size']`

## Correctness gate

- Full test suite: **223 passed**
- Existing pre-S0 tests retained: **205**
- New S0 tests: **18**
- Stored random seeds: `1729, 2718, 31415, 16180, 57721, 14142, 17320, 22360`
- Dense block sizes checked against scalar reference: `1, 3, 7, 256`
- Repeated deterministic runs checked: **4 per case**
- Ruff source lint: **passed**
- Python compileall: **passed**
- Wheel/source builds: **passed**
- Installed-wheel smoke test: **passed**

## Baseline harness

The machine-specific report is `benchmarks/dense_neighbors_benchmark.md`; raw records
are `benchmarks/dense_neighbors_benchmark.json`. Each record includes system size,
species counts, cutoff registry, center/candidate counts, dense pair evaluations,
accepted pair count, runtime samples, and peak traced memory.

The benchmark does not claim portable performance. It defines a reproducible
reference for comparing S1 cell-list crossover and memory behavior.

## Specification alignment

- Internal neighbor specification Markdown SHA-256: `b244284ba24ec189ec638884c7c1de7b910ae6095697729847dff360c178d4d9`
- Internal neighbor specification PDF SHA-256: `3acadcc7ab47842295c95da7177391380b6f20a0ea562e112e5fd1d8860deaed`
- Internal neighbor PDF pages/searchable characters: `11` / `18834`
- Staged plan Markdown SHA-256: `8441f66a873804229af44eb57f9d55b89e3918b662ec65d4d754c2c7ee37fe50`
- Staged plan PDF SHA-256: `2cc0d0ee2efe8e581550f93d84e4262683d604d2ca4505b937008604a4bd5e66`
- Staged plan PDF pages/searchable characters: `26` / `44547`

Alignment token checks:
- PASS: `NeighborSearchBackend`
- PASS: `DENSE`
- PASS: `backend`
- PASS: `canonicalize_neighbor_result`
- PASS: `compare_neighbor_results`
- PASS: `assert_neighbor_results_equal`
- PASS: `immutable`
- PASS: dense complexity section records `O(N_c N_n)`
- PASS: `Stage S0`
- PASS: `_build_dense_neighbor_list source only`
- PASS: `plan S0 complete`

## Deliberate deferrals

- No cell-list candidate generator.
- No lattice reduction or metric stencil.
- No persistent neighbor-search session.
- No fixed-cell or deformation-aware Verlet cache.
- No automatic backend policy.
- No consumer-module cache orchestration.

These remain stages S1-S4 and cannot be inferred from S0 passing.
